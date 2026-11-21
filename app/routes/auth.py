from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user
from app.extensions import db, bcrypt
from app.models.user import User
from app.models.category import Category
from app.forms import LoginForm, RegisterForm, PasswordResetRequestForm, PasswordResetForm
from urllib.parse import urlsplit
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from app.mail import mail_configured, public_base_url, send_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

DEFAULT_CATEGORIES = [
    ('Здоровье', 'heart', '#dc3545'),
    ('Спорт', 'trophy', '#fd7e14'),
    ('Продуктивность', 'lightning', '#ffc107'),
    ('Учёба', 'book', '#0d6efd'),
    ('Отдых', 'cup-hot', '#20c997'),
]


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tracking.today'))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Этот email уже зарегистрирован.', 'danger')
            return render_template('auth/register.html', form=form)

        if User.query.filter_by(username=form.username.data).first():
            flash('Это имя пользователя уже занято.', 'danger')
            return render_template('auth/register.html', form=form)

        user = User(
            email=form.email.data,
            username=form.username.data,
            password_hash=bcrypt.generate_password_hash(form.password.data).decode('utf-8'),
        )
        db.session.add(user)
        db.session.flush()

        for name, icon, color in DEFAULT_CATEGORIES:
            db.session.add(Category(name=name, icon=icon, color=color, user_id=user.id))

        db.session.commit()
        login_user(user)
        flash('Регистрация прошла успешно!', 'success')
        return redirect(url_for('tracking.today'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tracking.today'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            if not user.is_active_user:
                flash('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'danger')
                return render_template('auth/login.html', form=form)
            login_user(user)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/') or next_page.startswith('//') or '\\' in next_page or urlsplit(next_page).netloc:
                next_page = url_for('tracking.today')
            return redirect(next_page)
        flash('Неверный email или пароль.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('auth.login'))


def _password_stamp(user):
    return hmac.new(current_app.secret_key.encode() if isinstance(current_app.secret_key, str) else current_app.secret_key,
                    user.password_hash.encode(), hashlib.sha256).hexdigest()


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        if not mail_configured() or not public_base_url():
            flash('Восстановление пароля временно недоступно. Обратитесь к администратору.', 'warning')
            return redirect(url_for('auth.login'))
        user = User.query.filter_by(email=form.email.data, is_active_user=True).first()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if user and (not user.password_reset_sent_at or user.password_reset_sent_at <= now - timedelta(seconds=60)):
            token = URLSafeTimedSerializer(current_app.secret_key, salt='password-reset').dumps(
                {'user_id': user.id, 'stamp': _password_stamp(user)})
            link = public_base_url() + url_for('auth.reset_password', token=token)
            user.password_reset_sent_at = now
            db.session.commit()
            send_email(user.email, 'Восстановление пароля HabitFlow',
                       f'Чтобы изменить пароль, откройте ссылку в течение часа:\n{link}\n\nЕсли запрос не ваш, проигнорируйте письмо.')
        flash('Если аккаунт существует, письмо с инструкциями будет отправлено.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        payload = URLSafeTimedSerializer(current_app.secret_key, salt='password-reset').loads(
            token, max_age=current_app.config['PASSWORD_RESET_MAX_AGE'])
        user = db.session.get(User, payload['user_id'])
        if not user or not user.is_active_user or not hmac.compare_digest(payload['stamp'], _password_stamp(user)):
            raise BadSignature('invalid token')
    except (BadSignature, SignatureExpired, KeyError, TypeError, ValueError):
        flash('Ссылка недействительна или срок её действия истёк.', 'warning')
        return redirect(url_for('auth.forgot_password'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.password_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.api_token = None
        user.password_reset_sent_at = None
        db.session.commit()
        logout_user()
        flash('Пароль изменён. Войдите с новым паролем.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
