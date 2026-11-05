from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db, bcrypt
from app.models.user import User, ROLE_USER, ROLE_MODERATOR, ROLE_ADMIN
from app.models.habit import Habit
from app.models.habit_log import HabitLog

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def moderator_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_moderator:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@moderator_required
def dashboard():
    total_users = User.query.count()
    total_habits = Habit.query.count()
    total_logs = HabitLog.query.filter_by(completed=True).count()
    users = User.query.order_by(User.created_at.desc()).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_habits=total_habits,
                           total_logs=total_logs,
                           users=users)


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@admin_required
def change_role(user_id):
    if user_id == current_user.id:
        flash('Нельзя изменить свою роль.', 'danger')
        return redirect(url_for('admin.dashboard'))

    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    if new_role not in (ROLE_USER, ROLE_MODERATOR, ROLE_ADMIN):
        flash('Неверная роль.', 'danger')
        return redirect(url_for('admin.dashboard'))

    user.role = new_role
    db.session.commit()
    flash(f'Роль пользователя {user.username} изменена на {user.role_display}.', 'success')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    if user_id == current_user.id:
        flash('Нельзя заблокировать себя.', 'danger')
        return redirect(url_for('admin.dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_active_user = not user.is_active_user
    db.session.commit()
    action = 'разблокирован' if user.is_active_user else 'заблокирован'
    flash(f'Пользователь {user.username} {action}.', 'info')
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == current_user.id:
        flash('Нельзя удалить себя.', 'danger')
        return redirect(url_for('admin.dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Пользователь {user.username} удалён.', 'info')
    return redirect(url_for('admin.dashboard'))
