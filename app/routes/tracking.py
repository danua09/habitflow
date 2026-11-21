from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.habit import Habit
from app.models.habit_log import HabitLog

tracking_bp = Blueprint('tracking', __name__, url_prefix='/tracking')


@tracking_bp.route('/today')
@login_required
def today():
    today_date = date.today()
    day_map = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
    current_day = day_map[today_date.weekday()]

    habits = current_user.habits.filter_by(is_archived=False).all()
    today_habits = []
    for h in habits:
        if h.frequency == 'daily' or (h.frequency == 'weekly' and current_day in (h.target_days or [])):
            today_habits.append({
                'habit': h,
                'completed': h.is_completed_on(today_date),
                'streak': h.current_streak(),
            })

    completed_count = sum(1 for h in today_habits if h['completed'])
    total_count = len(today_habits)

    return render_template('tracking/today.html', habits=today_habits,
                           today=today_date, completed=completed_count, total=total_count,
                           has_any_habits=bool(habits))


@tracking_bp.route('/check/<int:habit_id>', methods=['POST'])
@login_required
def check(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    check_date = date.today()

    existing = HabitLog.query.filter_by(habit_id=habit.id, date=check_date).first()
    if not existing:
        log = HabitLog(habit_id=habit.id, date=check_date, completed=True)
        db.session.add(log)
        db.session.commit()

        from app.services import check_achievements_on_complete, log_activity
        check_achievements_on_complete(current_user.id)
        log_activity(current_user.id, 'check', f'выполнил(а) привычку «{habit.name}»')
        db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True, streak=habit.current_streak())
    return redirect(url_for('tracking.today'))


@tracking_bp.route('/uncheck/<int:habit_id>', methods=['POST'])
@login_required
def uncheck(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    check_date = date.today()

    log = HabitLog.query.filter_by(habit_id=habit.id, date=check_date).first()
    if log:
        db.session.delete(log)
        db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=True, streak=habit.current_streak())
    return redirect(url_for('tracking.today'))


@tracking_bp.route('/calendar/<int:habit_id>')
@login_required
def calendar(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    end_date = date.today()
    start_date = end_date - timedelta(days=365)

    logs = HabitLog.query.filter(
        HabitLog.habit_id == habit.id,
        HabitLog.date >= start_date,
        HabitLog.date <= end_date,
        HabitLog.completed == True,
    ).all()

    completed_dates = {log.date.isoformat() for log in logs}

    calendar_data = []
    current = start_date
    while current <= end_date:
        calendar_data.append({
            'date': current.isoformat(),
            'completed': current.isoformat() in completed_dates,
            'weekday': current.weekday(),
        })
        current += timedelta(days=1)

    return render_template('tracking/calendar.html', habit=habit,
                           calendar_data=calendar_data, streak=habit.current_streak(),
                           best_streak=habit.best_streak())
