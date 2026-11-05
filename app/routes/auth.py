from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.extensions import db, bcrypt
from app.models.user import User
from app.models.category import Category
from app.forms import LoginForm, RegisterForm

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
            return redirect(next_page or url_for('tracking.today'))
        flash('Неверный email или пароль.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('auth.login'))
