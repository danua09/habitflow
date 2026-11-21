import secrets
import hashlib
import hmac
from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db, login_manager

ROLE_USER = 'user'
ROLE_MODERATOR = 'moderator'
ROLE_ADMIN = 'admin'


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_USER)
    avatar_url = db.Column(db.String(255), default=None)
    is_active_user = db.Column(db.Boolean, default=True)
    bio = db.Column(db.String(300), default='')
    is_public = db.Column(db.Boolean, default=False)
    theme = db.Column(db.String(10), default='light')
    api_token = db.Column(db.String(64), unique=True, nullable=True, index=True)
    email_notifications = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    password_reset_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    habits = db.relationship('Habit', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    goals = db.relationship('Goal', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_active(self):
        return self.is_active_user

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    @property
    def is_moderator(self):
        return self.role in (ROLE_MODERATOR, ROLE_ADMIN)

    @property
    def role_display(self):
        return {'admin': 'Администратор', 'moderator': 'Модератор', 'user': 'Пользователь'}[self.role]

    def generate_api_token(self):
        self.api_token = secrets.token_hex(32)
        return self.api_token

    def get_id(self):
        digest = hashlib.sha256(self.password_hash.encode('utf-8')).hexdigest()
        return f'{self.id}:{digest}'

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    try:
        identity, digest = user_id.split(':', 1)
        user = db.session.get(User, int(identity))
    except (ValueError, AttributeError):
        return None
    if not user or not user.is_active_user or not hmac.compare_digest(user.get_id(), user_id):
        return None
    return user
