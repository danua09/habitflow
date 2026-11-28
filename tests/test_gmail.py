import base64
import io
import json
from email import policy
from email.parser import BytesParser
from urllib.error import HTTPError
from urllib.parse import parse_qs

import pytest

from app.mail import mail_configured, send_email


def configure(app):
    app.config.update(EMAIL_PROVIDER='gmail', MAIL_FROM='sender@gmail.com',
                      GMAIL_CLIENT_ID='client', GMAIL_CLIENT_SECRET='secret',
                      GMAIL_REFRESH_TOKEN='refresh')


def test_gmail_refresh_and_unicode_message(app, monkeypatch):
    configure(app)
    requests = []

    class Response(io.BytesIO):
        status = 200

    def fake_open(request, timeout):
        requests.append(request)
        return Response(b'{"access_token":"access"}' if len(requests) == 1 else b'{"id":"sent"}')

    monkeypatch.setattr('app.mail.urlopen', fake_open)
    assert send_email('receiver@example.com', 'Восстановление пароля', 'Ссылка: https://example.com/reset')
    assert requests[0].full_url == 'https://oauth2.googleapis.com/token'
    assert parse_qs(requests[0].data.decode())['grant_type'] == ['refresh_token']
    assert requests[1].full_url == 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
    assert requests[1].get_header('Authorization') == 'Bearer access'
    message = BytesParser(policy=policy.default).parsebytes(
        base64.urlsafe_b64decode(json.loads(requests[1].data)['raw']))
    assert message['To'] == 'receiver@example.com'
    assert message['From'] == 'sender@gmail.com'
    assert message['Subject'] == 'Восстановление пароля'
    assert 'https://example.com/reset' in message.get_content()


@pytest.mark.parametrize('failure_stage', [1, 2])
def test_gmail_failure_is_safe(app, monkeypatch, caplog, failure_stage):
    configure(app)
    calls = []

    def fake_open(request, timeout):
        calls.append(request)
        if len(calls) == failure_stage:
            raise HTTPError(request.full_url, 401, 'secret refresh', {}, None)
        return io.BytesIO(b'{"access_token":"access"}')

    monkeypatch.setattr('app.mail.urlopen', fake_open)
    assert not send_email('receiver@example.com', 'Subject', 'private body')
    assert 'secret refresh' not in caplog.text
    assert 'private body' not in caplog.text


def test_gmail_requires_all_credentials(app, monkeypatch):
    configure(app)
    app.config['GMAIL_REFRESH_TOKEN'] = ''
    assert not mail_configured()
    monkeypatch.setattr('app.mail.urlopen', lambda *a, **kw: pytest.fail('Network request without credentials'))
    assert not send_email('receiver@example.com', 'Subject', 'Body')
