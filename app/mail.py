"""Transactional email via SMTP, Resend or Gmail API."""
import base64
import smtplib
import ssl
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from email.message import EmailMessage
from urllib.parse import urlsplit, urlencode

from flask import current_app


def mail_configured():
    if current_app.config.get('EMAIL_PROVIDER') == 'gmail':
        return all(current_app.config.get(key) for key in (
            'GMAIL_CLIENT_ID', 'GMAIL_CLIENT_SECRET', 'GMAIL_REFRESH_TOKEN', 'MAIL_FROM'))
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
    if current_app.config.get('EMAIL_PROVIDER') == 'gmail':
        return _send_gmail(recipient, subject, body)
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


def _send_gmail(recipient, subject, body):
    """Refresh OAuth credentials server-side; never log tokens or message contents."""
    phase = 'refresh'
    try:
        message = EmailMessage()
        message['From'] = current_app.config['MAIL_FROM']
        message['To'] = recipient
        message['Subject'] = subject
        message.set_content(body)
        token_request = Request('https://oauth2.googleapis.com/token', data=urlencode({
            'client_id': current_app.config['GMAIL_CLIENT_ID'],
            'client_secret': current_app.config['GMAIL_CLIENT_SECRET'],
            'refresh_token': current_app.config['GMAIL_REFRESH_TOKEN'],
            'grant_type': 'refresh_token',
        }).encode('ascii'), method='POST')
        with urlopen(token_request, timeout=10) as response:
            access_token = json.load(response)['access_token']
        phase = 'send'
        payload = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}
        request = Request('https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                          data=json.dumps(payload).encode('utf-8'), method='POST', headers={
                              'Authorization': 'Bearer ' + access_token,
                              'Content-Type': 'application/json',
                          })
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except HTTPError as exc:
        try:
            payload = json.load(exc)
            error = payload.get('error', 'unknown')
            code = error.get('status', 'unknown') if isinstance(error, dict) else str(error)
        except (ValueError, OSError, TypeError):
            code = 'unknown'
        current_app.logger.warning('Gmail API %s failed: HTTP %s, %s', phase, exc.code, code)
        return False
    except (OSError, URLError, ValueError, KeyError, TypeError):
        current_app.logger.warning('Gmail API %s failed without HTTP response.', phase)
        return False
