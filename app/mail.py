"""Transactional email, enabled only when an SMTP service is configured."""
import smtplib
import ssl
import json
from urllib.request import Request, urlopen
from urllib.error import URLError
from email.message import EmailMessage
from urllib.parse import urlsplit

from flask import current_app


def mail_configured():
    if current_app.config.get('EMAIL_PROVIDER') == 'resend':
        return bool(current_app.config.get('RESEND_API_KEY') and current_app.config.get('MAIL_FROM'))
    return bool(current_app.config.get('SMTP_HOST') and current_app.config.get('SMTP_FROM') and
                (current_app.config.get('SMTP_USE_TLS') or not current_app.config.get('SESSION_COOKIE_SECURE')))


def public_base_url():
    value = current_app.config.get('PUBLIC_BASE_URL', '').rstrip('/')
    if not value and not current_app.config.get('SESSION_COOKIE_SECURE'):
        value = 'http://localhost:5050'
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        return None
    if current_app.config.get('SESSION_COOKIE_SECURE') and parsed.scheme != 'https':
        return None
    return value


def send_email(recipient, subject, body):
    if not mail_configured():
        return False
    if current_app.config.get('EMAIL_PROVIDER') == 'resend':
        data = json.dumps({'from': current_app.config['MAIL_FROM'], 'to': [recipient],
                           'subject': subject, 'text': body}).encode('utf-8')
        request = Request('https://api.resend.com/emails', data=data, method='POST', headers={
            'Authorization': 'Bearer ' + current_app.config['RESEND_API_KEY'],
            'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=10) as response:
                return 200 <= response.status < 300
        except (OSError, URLError):
            current_app.logger.warning('Не удалось отправить электронное письмо.')
            return False
    message = EmailMessage()
    message['From'] = current_app.config['SMTP_FROM']
    message['To'] = recipient
    message['Subject'] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(current_app.config['SMTP_HOST'], current_app.config['SMTP_PORT'], timeout=10) as smtp:
            if current_app.config['SMTP_USE_TLS']:
                smtp.starttls(context=ssl.create_default_context())
            if current_app.config['SMTP_USERNAME']:
                smtp.login(current_app.config['SMTP_USERNAME'], current_app.config['SMTP_PASSWORD'])
            smtp.send_message(message)
        return True
    except (OSError, smtplib.SMTPException):
        current_app.logger.warning('Не удалось отправить электронное письмо.')
        return False
