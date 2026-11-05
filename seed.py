from app import create_app
from app.extensions import db, bcrypt
from app.models.user import User, ROLE_ADMIN, ROLE_MODERATOR, ROLE_USER
from app.models.category import Category
from app.models.template import HabitTemplate, TemplateHabit
from app.services import seed_achievements

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()

    admin = User(
        email='admin@habitflow.com',
        username='admin',
        password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
        role=ROLE_ADMIN,
        bio='Администратор платформы HabitFlow',
        is_public=True,
    )
    db.session.add(admin)
    db.session.flush()

    moderator = User(
        email='moderator@habitflow.com',
        username='moderator',
        password_hash=bcrypt.generate_password_hash('mod123').decode('utf-8'),
        role=ROLE_MODERATOR,
        bio='Модератор контента',
        is_public=True,
    )
    db.session.add(moderator)
    db.session.flush()

    user = User(
        email='user@habitflow.com',
        username='user',
        password_hash=bcrypt.generate_password_hash('user123').decode('utf-8'),
        role=ROLE_USER,
        bio='Обычный пользователь HabitFlow',
        is_public=True,
    )
    db.session.add(user)
    db.session.flush()

    for u in [admin, moderator, user]:
        for name, icon, color in [
            ('Здоровье', 'heart', '#dc3545'),
            ('Спорт', 'trophy', '#fd7e14'),
            ('Продуктивность', 'lightning', '#ffc107'),
            ('Учёба', 'book', '#0d6efd'),
            ('Отдых', 'cup-hot', '#20c997'),
        ]:
            db.session.add(Category(name=name, icon=icon, color=color, user_id=u.id))

    seed_achievements()

    t1 = HabitTemplate(name='Здоровый образ жизни', description='Базовые привычки для поддержания здоровья',
                       icon='heart-pulse', color='#dc3545', is_public=True, created_by=admin.id)
    db.session.add(t1)
    db.session.flush()
    for name, color in [('Утренняя зарядка', '#fd7e14'), ('Выпить 8 стаканов воды', '#0ea5e9'),
                         ('Сон до 23:00', '#8b5cf6'), ('Прогулка 30 минут', '#16a34a')]:
        db.session.add(TemplateHabit(template_id=t1.id, name=name, color=color))

    t2 = HabitTemplate(name='Продуктивность', description='Привычки для повышения эффективности',
                       icon='lightning', color='#f59e0b', is_public=True, created_by=admin.id)
    db.session.add(t2)
    db.session.flush()
    for name, color in [('Чтение 30 минут', '#0d6efd'), ('Медитация 10 минут', '#8b5cf6'),
                         ('Планирование дня', '#f59e0b'), ('Без соцсетей до обеда', '#ef4444')]:
        db.session.add(TemplateHabit(template_id=t2.id, name=name, color=color))

    t3 = HabitTemplate(name='Спорт и фитнес', description='Регулярные тренировки и активный образ жизни',
                       icon='bicycle', color='#16a34a', is_public=True, created_by=admin.id)
    db.session.add(t3)
    db.session.flush()
    for name, color in [('Тренировка', '#ef4444'), ('Растяжка', '#f59e0b'),
                         ('10 000 шагов', '#16a34a')]:
        db.session.add(TemplateHabit(template_id=t3.id, name=name, color=color))

    db.session.commit()
    print('Database seeded!')
    print('Admin:     admin@habitflow.com / admin123')
    print('Moderator: moderator@habitflow.com / mod123')
    print('User:      user@habitflow.com / user123')
    print('Achievements: 13 created')
    print('Templates: 3 public templates created')
    print('All users have public profiles enabled')
