"""Set up a local PostgreSQL database without exposing the password in commands."""
import getpass
import locale
import os
from pathlib import Path
import subprocess
import sys

import psycopg2
from psycopg2 import sql
from dotenv import dotenv_values, set_key
from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / '.env'
DATABASE = 'habitflow'


def main():
    if dotenv_values(ENV_FILE).get('DATABASE_URL'):
        sys.exit('DATABASE_URL уже задан в .env. Настройка отменена, чтобы его не перезаписать.')

    password = getpass.getpass('Пароль пользователя PostgreSQL postgres: ')
    settings = {'host': 'localhost', 'port': 5432, 'user': 'postgres', 'password': password}
    try:
        connection = psycopg2.connect(dbname='postgres', **settings)
        try:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 FROM pg_database WHERE datname = %s', (DATABASE,))
                if not cursor.fetchone():
                    cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(DATABASE)))
        finally:
            connection.close()

        with psycopg2.connect(dbname=DATABASE, **settings) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' LIMIT 1")
                if cursor.fetchone():
                    sys.exit('База habitflow уже содержит таблицы. Настройка отменена для сохранения данных.')
    except UnicodeDecodeError as exc:
        # libpq may return a localized Windows error in the system code page.
        message = exc.object.decode(locale.getpreferredencoding(False), errors='replace').strip()
        sys.exit(f'Не удалось подготовить PostgreSQL: {message}')
    except psycopg2.Error as exc:
        sys.exit(f'Не удалось подготовить PostgreSQL: {exc.pgerror or str(exc)}')

    database_url = URL.create('postgresql+psycopg2', username='postgres', password=password,
                              host='localhost', port=5432, database=DATABASE).render_as_string(hide_password=False)
    env = os.environ.copy()
    env['DATABASE_URL'] = database_url
    print('Создание таблиц...', flush=True)
    subprocess.run([sys.executable, '-m', 'flask', '--app', 'run', 'db', 'upgrade'],
                   cwd=ROOT, env=env, check=True)
    print('Добавление списка достижений...', flush=True)
    subprocess.run([sys.executable, '-c',
                    'from app import create_app; from app.services import seed_achievements; '
                    'app = create_app(); ctx = app.app_context(); ctx.push(); '
                    'seed_achievements(); ctx.pop()'], cwd=ROOT, env=env, check=True)
    ENV_FILE.touch(exist_ok=True)
    set_key(str(ENV_FILE), 'DATABASE_URL', database_url)
    print('Готово: приложение подключено к базе PostgreSQL habitflow.')


if __name__ == '__main__':
    main()
