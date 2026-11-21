import os
from sqlalchemy.engine import URL

basedir = os.path.abspath(os.path.dirname(__file__))


def database_url():
    if os.environ.get('POSTGRES_HOST'):
        return URL.create('postgresql+psycopg2', username=os.environ['POSTGRES_USER'],
                          password=os.environ['POSTGRES_PASSWORD'], host=os.environ['POSTGRES_HOST'],
                          port=int(os.environ.get('POSTGRES_PORT', '5432')),
                          database=os.environ['POSTGRES_DB'])
    url = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(basedir), 'habit_tracker.db')
    )
    if url.startswith('postgres://'):
        return 'postgresql+psycopg2://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SMTP_HOST = os.environ.get('SMTP_HOST', '')
    EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', 'smtp').lower()
    RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
    MAIL_FROM = os.environ.get('MAIL_FROM', '')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_FROM = os.environ.get('SMTP_FROM', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL') or os.environ.get('RENDER_EXTERNAL_URL', '')
    PASSWORD_RESET_MAX_AGE = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
