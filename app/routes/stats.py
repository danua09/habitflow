import csv
import io
from datetime import date, timedelta
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from app.models.habit import Habit
from app.models.habit_log import HabitLog

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


@stats_bp.route('/')
@login_required
def dashboard():
    today_date = date.today()
    habits = current_user.habits.filter_by(is_archived=False).all()

    today_completed = 0
    today_total = 0
    day_map = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
    current_day = day_map[today_date.weekday()]

    for h in habits:
        if h.frequency == 'daily' or (h.frequency == 'weekly' and current_day in (h.target_days or [])):
            today_total += 1
            if h.is_completed_on(today_date):
                today_completed += 1

    week_start = today_date - timedelta(days=today_date.weekday())
    week_data = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        completed = 0
        total = 0
        day_key = day_map[d.weekday()]
        for h in habits:
            if h.frequency == 'daily' or (h.frequency == 'weekly' and day_key in (h.target_days or [])):
                total += 1
                if h.is_completed_on(d):
                    completed += 1
        week_data.append({'date': d.isoformat(), 'day': d.strftime('%a'), 'completed': completed, 'total': total})

    habit_stats = []
    for h in habits:
        habit_stats.append({
            'habit': h,
            'rate_7': h.completion_rate(7),
            'rate_30': h.completion_rate(30),
            'streak': h.current_streak(),
            'best_streak': h.best_streak(),
        })
    habit_stats.sort(key=lambda x: x['rate_30'], reverse=True)

    return render_template('stats/dashboard.html',
                           today_completed=today_completed, today_total=today_total,
                           week_data=week_data, habit_stats=habit_stats)


@stats_bp.route('/habit/<int:habit_id>')
@login_required
def habit_detail(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()

    days = int(request.args.get('days', 30))
    today_date = date.today()
    daily_data = []
    for i in range(days - 1, -1, -1):
        d = today_date - timedelta(days=i)
        daily_data.append({
            'date': d.isoformat(),
            'label': d.strftime('%d.%m'),
            'completed': 1 if habit.is_completed_on(d) else 0,
        })

    return render_template('stats/habit_detail.html', habit=habit,
                           daily_data=daily_data, days=days,
                           rate=habit.completion_rate(days),
                           streak=habit.current_streak(),
                           best_streak=habit.best_streak())


@stats_bp.route('/export')
@login_required
def export_csv():
    habits = current_user.habits.filter_by(is_archived=False).all()
    today_date = date.today()
    start = today_date - timedelta(days=89)

    output = io.StringIO()
    writer = csv.writer(output)
    header = ['Привычка', 'Категория'] + [(start + timedelta(days=i)).isoformat() for i in range(90)]
    writer.writerow(header)

    for h in habits:
        logs = {log.date.isoformat() for log in
                HabitLog.query.filter(HabitLog.habit_id == h.id, HabitLog.date >= start,
                                       HabitLog.completed == True).all()}
        row = [h.name, h.category.name if h.category else '']
        for i in range(90):
            d = (start + timedelta(days=i)).isoformat()
            row.append('1' if d in logs else '0')
        writer.writerow(row)

    output.seek(0)
    return Response(
        '﻿' + output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=habits_export_{today_date}.csv'},
    )
