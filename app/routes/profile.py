from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user, login_user
from app.extensions import db, bcrypt
from app.models.user import User
from app.forms import ProfileForm, ChangePasswordForm

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')


@profile_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        if form.email.data != current_user.email:
            if User.query.filter_by(email=form.email.data).first():
                flash('Этот email уже занят.', 'danger')
                return render_template('profile/index.html', form=form)

        if form.username.data != current_user.username:
            if User.query.filter_by(username=form.username.data).first():
                flash('Это имя пользователя уже занято.', 'danger')
                return render_template('profile/index.html', form=form)

        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.bio = request.form.get('bio', '').strip()[:300]
        current_user.is_public = 'is_public' in request.form
        current_user.email_notifications = 'email_notifications' in request.form
        db.session.commit()
        flash('Профиль обновлён!', 'success')
        return redirect(url_for('profile.index'))

    return render_template('profile/index.html', form=form)


@profile_bp.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not bcrypt.check_password_hash(current_user.password_hash, form.current_password.data):
            flash('Неверный текущий пароль.', 'danger')
            return render_template('profile/password.html', form=form)

        current_user.password_hash = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
        current_user.api_token = None
        db.session.commit()
        login_user(current_user)
        flash('Пароль изменён!', 'success')
        return redirect(url_for('profile.index'))

    return render_template('profile/password.html', form=form)


@profile_bp.route('/theme', methods=['POST'])
@login_required
def change_theme():
    data = request.get_json()
    theme = data.get('theme', 'light')
    if theme not in ('light', 'dark'):
        theme = 'light'
    current_user.theme = theme
    db.session.commit()
    return jsonify({'theme': theme})


@profile_bp.route('/api-token', methods=['POST'])
@login_required
def generate_token():
    token = current_user.generate_api_token()
    db.session.commit()
    flash(f'API-токен сгенерирован: {token}', 'success')
    return redirect(url_for('profile.index'))
