from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.social import Friendship, Challenge, ActivityLog
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
            ActivityLog.user_id.in_(friend_ids)
        ).order_by(ActivityLog.created_at.desc()).limit(30).all()

    active_challenges = Challenge.query.filter(
        ((Challenge.creator_id == current_user.id) | (Challenge.opponent_id == current_user.id)),
        Challenge.status.in_(['pending', 'active']),
    ).order_by(Challenge.created_at.desc()).all()

    return render_template('social/index.html', friends=friends, incoming=incoming,
                           activities=activities, challenges=active_challenges)


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


# --- Challenges ---

@social_bp.route('/challenge/create/<int:friend_id>', methods=['GET', 'POST'])
@login_required
def create_challenge(friend_id):
    friend = User.query.get_or_404(friend_id)
    friends = get_friends(current_user.id)
    if friend not in friends:
        flash('Можно челленджить только друзей.', 'danger')
        return redirect(url_for('social.index'))

    if request.method == 'POST':
        habit_name = request.form.get('habit_name', '').strip()
        description = request.form.get('description', '').strip()
        duration = int(request.form.get('duration', 7))
        if duration not in (7, 14, 30):
            duration = 7

        if not habit_name:
            flash('Название привычки обязательно.', 'danger')
            return redirect(url_for('social.create_challenge', friend_id=friend_id))

        challenge = Challenge(
            creator_id=current_user.id, opponent_id=friend_id,
            habit_name=habit_name, description=description,
            duration_days=duration, status='pending',
        )
        db.session.add(challenge)

        from app.services import create_notification
        create_notification(friend_id,
                            f'{current_user.username} бросил(а) вам челлендж: {habit_name}!',
                            link='/social/')
        db.session.commit()
        flash('Челлендж отправлен!', 'success')
        return redirect(url_for('social.index'))

    return render_template('social/challenge_form.html', friend=friend)


@social_bp.route('/challenge/<int:challenge_id>/accept', methods=['POST'])
@login_required
def accept_challenge(challenge_id):
    c = Challenge.query.get_or_404(challenge_id)
    if c.opponent_id != current_user.id:
        flash('Нет прав.', 'danger')
        return redirect(url_for('social.index'))

    today = date.today()
    c.status = 'active'
    c.start_date = today
    c.end_date = today + timedelta(days=c.duration_days)

    for user_id in (c.creator_id, c.opponent_id):
        existing = Habit.query.filter_by(user_id=user_id, name=c.habit_name).first()
        if not existing:
            habit = Habit(user_id=user_id, name=c.habit_name, color='#ef4444',
                          description=f'Челлендж с другом')
            db.session.add(habit)

    log_activity(current_user.id, 'challenge', f'принял(а) челлендж «{c.habit_name}»')

    from app.services import create_notification
    create_notification(c.creator_id,
                        f'{current_user.username} принял(а) челлендж «{c.habit_name}»!',
                        link='/social/')
    db.session.commit()
    flash('Челлендж начался!', 'success')
    return redirect(url_for('social.index'))


@social_bp.route('/challenge/<int:challenge_id>/decline', methods=['POST'])
@login_required
def decline_challenge(challenge_id):
    c = Challenge.query.get_or_404(challenge_id)
    if c.opponent_id != current_user.id:
        flash('Нет прав.', 'danger')
        return redirect(url_for('social.index'))

    c.status = 'declined'
    db.session.commit()
    flash('Челлендж отклонён.', 'info')
    return redirect(url_for('social.index'))


@social_bp.route('/challenge/<int:challenge_id>')
@login_required
def view_challenge(challenge_id):
    c = Challenge.query.get_or_404(challenge_id)
    if c.creator_id != current_user.id and c.opponent_id != current_user.id:
        flash('Нет доступа.', 'danger')
        return redirect(url_for('social.index'))

    creator_score = 0
    opponent_score = 0
    if c.status == 'active' and c.start_date:
        end = min(c.end_date, date.today()) if c.end_date else date.today()
        current = c.start_date
        while current <= end:
            for h in Habit.query.filter_by(user_id=c.creator_id, name=c.habit_name).all():
                if h.is_completed_on(current):
                    creator_score += 1
                    break
            for h in Habit.query.filter_by(user_id=c.opponent_id, name=c.habit_name).all():
                if h.is_completed_on(current):
                    opponent_score += 1
                    break
            current += timedelta(days=1)

    return render_template('social/challenge_view.html', challenge=c,
                           creator_score=creator_score, opponent_score=opponent_score)
