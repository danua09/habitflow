import pytest
import os
import re
from datetime import datetime, timedelta, timezone
from sqlalchemy.engine import make_url
from app import create_app
from app.extensions import db as _db, bcrypt
from app.models.user import User, ROLE_USER, ROLE_ADMIN
from app.models.category import Category
from app.models.habit import Habit
from app.services import seed_achievements


@pytest.fixture
def app():
    test_url = os.environ.get('HABITFLOW_TEST_DATABASE_URL', 'sqlite://')
    if test_url != 'sqlite://':
        url = make_url(test_url)
        if url.get_backend_name() != 'postgresql' or not re.fullmatch(r'habitflow_test_[0-9a-f]{32}', url.database or ''):
            raise RuntimeError('Тесты разрешены только на временной тестовой базе habitflow_test_<uuid>.')
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_url,
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
    })
    with app.app_context():
        _db.create_all()
        seed_achievements()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    u = User(
        email='test@example.com',
        username='testuser',
        password_hash=bcrypt.generate_password_hash('password123').decode('utf-8'),
        role=ROLE_USER,
    )
    _db.session.add(u)
    _db.session.commit()
    return u


@pytest.fixture
def admin(app):
    a = User(
        email='admin@example.com',
        username='testadmin',
        password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
        role=ROLE_ADMIN,
    )
    _db.session.add(a)
    _db.session.flush()
    return a


@pytest.fixture
def category(app, user):
    c = Category(name='Тест', icon='star', color='#ff0000', user_id=user.id)
    _db.session.add(c)
    _db.session.flush()
    return c


@pytest.fixture
def habit(app, user, category):
    h = Habit(
        user_id=user.id,
        category_id=category.id,
        name='Утренняя зарядка',
        frequency='daily',
        color='#0d6efd',
        created_at=datetime.now(timezone.utc) - timedelta(days=30),
    )
    _db.session.add(h)
    _db.session.flush()
    return h
