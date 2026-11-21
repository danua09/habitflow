"""Populate achievement definitions and, optionally, a separate demo account."""
import argparse
import getpass
import os
from datetime import date, datetime, timedelta, timezone

from app import create_app
from app.extensions import bcrypt, db
from app.models.category import Category
from app.models.goal import Goal
from app.models.habit import Habit
from app.models.habit_log import HabitLog
from app.models.user import User, ROLE_ADMIN
from app.routes.auth import DEFAULT_CATEGORIES
from app.services import seed_achievements


def seed_demo(password):
    email, username = 'demo@example.com', 'demo_habitflow'
    if User.query.filter((User.email == email) | (User.username == username)).first():
        raise SystemExit('Демонстрационный пользователь уже существует; данные не изменены.')
    if len(password) < 10:
        raise SystemExit('Демонстрационный пароль должен содержать не менее 10 символов.')
    start = datetime.now(timezone.utc) - timedelta(days=14)
    user = User(email=email, username=username, role=ROLE_ADMIN,
                password_hash=bcrypt.generate_password_hash(password).decode('utf-8'), created_at=start)
    db.session.add(user)
    db.session.flush()
    categories = []
    for name, icon, color in DEFAULT_CATEGORIES:
        category = Category(user_id=user.id, name=name, icon=icon, color=color)
        db.session.add(category)
        categories.append(category)
    db.session.flush()
    habits = [Habit(user_id=user.id, category_id=categories[1].id, name='Утренняя зарядка',
                    frequency='daily', color='#fd7e14', created_at=start),
              Habit(user_id=user.id, category_id=categories[3].id, name='Чтение 20 минут',
                    frequency='weekly', target_days=['mon', 'wed', 'fri'], color='#0d6efd', created_at=start)]
    db.session.add_all(habits)
    db.session.flush()
    for habit in habits:
        for offset in range(14):
            day = date.today() - timedelta(days=offset)
            if habit.is_scheduled_on(day) and offset not in (3, 8):
                db.session.add(HabitLog(habit_id=habit.id, date=day, completed=True))
    goal = Goal(user_id=user.id, title='Поддерживать здоровый и продуктивный ритм',
                description='Регулярная зарядка и чтение', deadline=date.today() + timedelta(days=30),
                created_at=start)
    goal.habits.extend(habits)
    db.session.add(goal)
    db.session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', help='создать отдельный демонстрационный аккаунт')
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        seed_achievements()
        if args.demo:
            password = os.environ.get('HABITFLOW_DEMO_PASSWORD') or getpass.getpass('Пароль демонстрационного аккаунта: ')
            seed_demo(password)
            print('Демонстрационный аккаунт создан: demo@example.com')
        else:
            print('Список достижений проверен.')


if __name__ == '__main__':
    main()
