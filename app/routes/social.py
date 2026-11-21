from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.social import Friendship, ActivityLog
from app.models.habit import Habit
from app.models.habit_log import HabitLog

social_bp = Blueprint('social', __name__, url_prefix='/social')


def log_activity(user_id, action, description=''):
    db.session.add(ActivityLog(user_id=user_id, action=action, description=description))


def get_friends(user_id):
    accepted = Friendship.query.filter(
        ((Friendship.user_id == user_id) | (Friendship.friend_id == user_id)),
        Friendship.status == 'accepted',
    ).all()
    friend_ids = set()
    for f in accepted:
        friend_ids.add(f.friend_id if f.user_id == user_id else f.user_id)
    return User.query.filter(User.id.in_(friend_ids)).all() if friend_ids else []


@social_bp.route('/')
@login_required
def index():
    friends = get_friends(current_user.id)
    friend_ids = [f.id for f in friends]

    incoming = Friendship.query.filter_by(friend_id=current_user.id, status='pending').all()

    activities = []
    if friend_ids:
        activities = ActivityLog.query.filter(
            ActivityLog.user_id.in_(friend_ids), ActivityLog.action != 'challenge'
        ).order_by(ActivityLog.created_at.desc()).limit(30).all()

    return render_template('social/index.html', friends=friends, incoming=incoming,
                           activities=activities)

@social_bp.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    users = []
    if q:
        users = User.query.filter(
            User.id != current_user.id,
            User.is_public == True,
            (User.username.ilike(f'%{q}%') | User.email.ilike(f'%{q}%')),
        ).limit(20).all()
    return render_template('social/search.html', users=users, query=q)


@social_bp.route('/add/<int:user_id>', methods=['POST'])
@login_required
def add_friend(user_id):
    if user_id == current_user.id:
        flash('Нельзя добавить себя.', 'danger')
        return redirect(url_for('social.index'))

    target = User.query.get_or_404(user_id)

    existing = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user_id)) |
        ((Friendship.user_id == user_id) & (Friendship.friend_id == current_user.id))
    ).first()

    if existing:
        flash('Запрос уже существует.', 'info')
        return redirect(url_for('social.index'))

    f = Friendship(user_id=current_user.id, friend_id=user_id, status='pending')
    db.session.add(f)

    from app.services import create_notification
    create_notification(user_id,
                        f'{current_user.username} хочет добавить вас в друзья',
                        link='/social/')
    db.session.commit()
    flash(f'Запрос дружбы отправлен {target.username}!', 'success')
    return redirect(url_for('social.search'))


@social_bp.route('/accept/<int:friendship_id>', methods=['POST'])
@login_required
def accept_friend(friendship_id):
    f = Friendship.query.get_or_404(friendship_id)
    if f.friend_id != current_user.id:
        flash('Нет прав.', 'danger')
        return redirect(url_for('social.index'))

    f.status = 'accepted'
    log_activity(current_user.id, 'friend', f'стал(а) другом {f.user.username}')
    log_activity(f.user_id, 'friend', f'стал(а) другом {current_user.username}')

    from app.services import create_notification
    create_notification(f.user_id,
                        f'{current_user.username} принял(а) запрос дружбы!',
                        link='/social/')
    db.session.commit()
    flash('Запрос принят!', 'success')
    return redirect(url_for('social.index'))


@social_bp.route('/reject/<int:friendship_id>', methods=['POST'])
@login_required
def reject_friend(friendship_id):
    f = Friendship.query.get_or_404(friendship_id)
    if f.friend_id != current_user.id:
        flash('Нет прав.', 'danger')
        return redirect(url_for('social.index'))

    db.session.delete(f)
    db.session.commit()
    flash('Запрос отклонён.', 'info')
    return redirect(url_for('social.index'))


@social_bp.route('/remove/<int:user_id>', methods=['POST'])
@login_required
def remove_friend(user_id):
    f = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user_id)) |
        ((Friendship.user_id == user_id) & (Friendship.friend_id == current_user.id)),
        Friendship.status == 'accepted',
    ).first_or_404()

    db.session.delete(f)
    db.session.commit()
    flash('Друг удалён.', 'info')
    return redirect(url_for('social.index'))


@social_bp.route('/profile/<int:user_id>')
@login_required
def public_profile(user_id):
    user = User.query.get_or_404(user_id)
    if not user.is_public and user.id != current_user.id:
        flash('Профиль закрыт.', 'info')
        return redirect(url_for('social.index'))

    habits_count = user.habits.filter_by(is_archived=False).count()
    total_logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == user.id, HabitLog.completed == True
    ).count()

    best_streak = 0
    for h in user.habits.filter_by(is_archived=False).all():
        s = h.best_streak()
        if s > best_streak:
            best_streak = s

    from app.models.achievement import UserAchievement
    achievements_count = UserAchievement.query.filter_by(user_id=user.id).count()

    is_friend = False
    friendship = Friendship.query.filter(
        ((Friendship.user_id == current_user.id) & (Friendship.friend_id == user_id)) |
        ((Friendship.user_id == user_id) & (Friendship.friend_id == current_user.id)),
    ).first()
    if friendship and friendship.status == 'accepted':
        is_friend = True

    return render_template('social/profile.html', user=user, habits_count=habits_count,
                           total_logs=total_logs, best_streak=best_streak,
                           achievements_count=achievements_count, is_friend=is_friend,
                           friendship=friendship)
