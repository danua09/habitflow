"""Obtain a Gmail API refresh token for a personal Desktop OAuth client.

Run locally with: python setup_gmail_oauth.py
The refresh token is printed once for manual entry into Render; it is never
written to disk or logged by this script.
"""
import http.server
import base64
import getpass
import hashlib
import json
import secrets
import socket
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser


SCOPE = 'https://www.googleapis.com/auth/gmail.send'
AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


def check_existing_token():
    client_id = input('OAuth Client ID: ').strip()
    client_secret = getpass.getpass('OAuth Client secret (ввод скрыт): ').strip()
    refresh_token = getpass.getpass('Gmail refresh token (ввод скрыт): ').strip()
    if not all((client_id, client_secret, refresh_token)):
        raise SystemExit('Все три значения обязательны.')
    request = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }).encode('ascii'), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            code = json.loads(exc.read()).get('error', 'unknown_error')
        except (ValueError, OSError):
            code = 'unknown_error'
        raise SystemExit(f'Проверка не прошла: HTTP {exc.code}, {code}. Не отправляй токен в чат.') from None
    except (urllib.error.URLError, ValueError):
        raise SystemExit('Не удалось получить ответ Google. Проверь подключение.') from None
    if not payload.get('access_token'):
        raise SystemExit('Google не вернул access token.')
    print('Токен действителен для этого OAuth-клиента.')


def main():
    if sys.argv[1:] == ['--check']:
        check_existing_token()
        return
    if sys.argv[1:]:
        raise SystemExit('Использование: python setup_gmail_oauth.py [--check]')
    client_id = input('Вставь OAuth Client ID (он не секретный): ').strip()
    client_secret = getpass.getpass('Вставь OAuth Client secret (ввод скрыт): ').strip()
    if not client_id or not client_secret:
        raise SystemExit('Client ID и Client secret обязательны.')

    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')
    result = {}
    ready = threading.Event()

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            if parsed.path != '/oauth2callback' or params.get('state', [''])[0] != state:
                self.send_error(400, 'Invalid OAuth callback')
                return
            if 'error' in params:
                result['error'] = params['error'][0]
            elif 'code' in params:
                result['code'] = params['code'][0]
            self.send_response(200 if 'code' in result else 400)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(('Авторизация завершена. Можно закрыть это окно.' if 'code' in result
                              else 'Авторизация не завершена. Вернись в консоль.').encode('utf-8'))
            ready.set()

        def log_message(self, *_args):
            pass

    # Bind only to loopback; do not expose the callback listener to the network.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    redirect_uri = f'http://127.0.0.1:{port}/oauth2callback'
    server = http.server.HTTPServer(('127.0.0.1', port), CallbackHandler)
    server.timeout = 300
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    query = urllib.parse.urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': SCOPE,
        'access_type': 'offline',
        'prompt': 'consent',
        'include_granted_scopes': 'true',
        'state': state,
        'code_challenge': challenge,
        'code_challenge_method': 'S256',
    })
    authorization_url = f'{AUTH_URL}?{query}'
    print('\nОткроется Google. Проверь аккаунт и разрешение только на отправку писем.')
    print('Если браузер не открылся, открой эту ссылку вручную:\n' + authorization_url)
    webbrowser.open(authorization_url)
    ready.wait(300)
    server.server_close()
    if 'error' in result:
        raise SystemExit('Google отменил авторизацию: ' + result['error'])
    if 'code' not in result:
        raise SystemExit('Не получен ответ Google за 5 минут. Запусти скрипт повторно.')

    request = urllib.request.Request(TOKEN_URL, data=urllib.parse.urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'code': result['code'],
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
        'code_verifier': verifier,
    }).encode('ascii'), headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            tokens = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            error_code = json.loads(exc.read()).get('error', 'unknown_error')
        except (ValueError, OSError):
            error_code = 'unknown_error'
        raise SystemExit(f'Google отклонил обмен кода: HTTP {exc.code}, {error_code}. '
                         'Секреты и ссылку авторизации не присылай.') from None
    except (urllib.error.URLError, ValueError) as exc:
        raise SystemExit('Не удалось получить ответ Google. Проверь подключение и попробуй снова.') from exc

    refresh_token = tokens.get('refresh_token')
    if not refresh_token:
        raise SystemExit('Google не вернул refresh_token. Отзови доступ у приложения Google и повтори авторизацию.')
    print('\nГотово. Скопируй значения в Render → habitflow → Environment:')
    print('EMAIL_PROVIDER=gmail')
    print('MAIL_FROM=твой адрес Gmail')
    print('GMAIL_CLIENT_ID=' + client_id)
    print('GMAIL_CLIENT_SECRET=вставь Client secret из Google Cloud')
    print('GMAIL_REFRESH_TOKEN=' + refresh_token)
    print('PUBLIC_BASE_URL=https://habitflow-r87t.onrender.com')
    print('\nНе отправляй этот вывод в чат и не сохраняй его в Git.')


if __name__ == '__main__':
    main()
