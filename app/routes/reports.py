import io
from datetime import date, timedelta
from flask import Blueprint, render_template, Response
from flask_login import login_required, current_user
from app.models.habit import Habit
from app.models.habit_log import HabitLog
from app.models.achievement import UserAchievement
from app.models.goal import Goal

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


def _get_period_stats(user_id, start, end):
    habits = Habit.query.filter_by(user_id=user_id, is_archived=False).all()
    total_possible = 0
    total_done = 0
    day_map = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}

    current = start
    while current <= end:
        day_key = day_map[current.weekday()]
        for h in habits:
            if h.frequency == 'daily' or (h.frequency == 'weekly' and day_key in (h.target_days or [])):
                total_possible += 1
                if h.is_completed_on(current):
                    total_done += 1
        current += timedelta(days=1)

    rate = round(total_done / total_possible * 100, 1) if total_possible else 0
    return {'total_possible': total_possible, 'total_done': total_done, 'rate': rate}


@reports_bp.route('/')
@login_required
def index():
    today = date.today()
    habits = current_user.habits.filter_by(is_archived=False).all()

    week_start = today - timedelta(days=today.weekday())
    week_end = today
    month_start = today.replace(day=1)

    week_stats = _get_period_stats(current_user.id, week_start, week_end)
    month_stats = _get_period_stats(current_user.id, month_start, today)

    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    prev_month_stats = _get_period_stats(current_user.id, prev_month_start, prev_month_end)

    comparison = {
        'current': month_stats['rate'],
        'previous': prev_month_stats['rate'],
        'diff': round(month_stats['rate'] - prev_month_stats['rate'], 1),
    }

    habit_rankings = []
    for h in habits:
        habit_rankings.append({
            'habit': h,
            'rate_7': h.completion_rate(7),
            'rate_30': h.completion_rate(30),
            'streak': h.current_streak(),
            'best_streak': h.best_streak(),
        })
    habit_rankings.sort(key=lambda x: x['rate_30'], reverse=True)

    recommendations = _generate_recommendations(habits, habit_rankings)

    total_logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == current_user.id, HabitLog.completed == True
    ).count()
    achievements_earned = UserAchievement.query.filter_by(user_id=current_user.id).count()
    goals_completed = Goal.query.filter_by(user_id=current_user.id, status='completed').count()

    forecast = _forecast_goals(current_user.id)

    return render_template('reports/index.html',
                           week_stats=week_stats, month_stats=month_stats,
                           comparison=comparison, habit_rankings=habit_rankings,
                           recommendations=recommendations, total_logs=total_logs,
                           achievements_earned=achievements_earned,
                           goals_completed=goals_completed, forecast=forecast)


def _generate_recommendations(habits, rankings):
    recs = []
    if not habits:
        recs.append({'icon': 'plus-circle', 'color': '#16a34a',
                     'text': 'Создайте первую привычку, чтобы начать отслеживание!'})
        return recs

    for r in rankings:
        if r['rate_30'] < 20 and r['rate_30'] > 0:
            recs.append({'icon': 'arrow-down-circle', 'color': '#ef4444',
                         'text': f'Привычка «{r["habit"].name}» выполняется редко ({r["rate_30"]}%). '
                                 f'Попробуйте упростить её или изменить расписание.'})
        if r['streak'] >= 7:
            recs.append({'icon': 'fire', 'color': '#f59e0b',
                         'text': f'Отличная серия у «{r["habit"].name}» — {r["streak"]} дней! Продолжайте!'})

    if len(rankings) >= 3:
        top = rankings[0]
        if top['rate_30'] >= 80:
            recs.append({'icon': 'star', 'color': '#8b5cf6',
                         'text': f'«{top["habit"].name}» — ваша лучшая привычка ({top["rate_30"]}%). '
                                 f'Рассмотрите добавление новой привычки.'})

    low_count = sum(1 for r in rankings if r['rate_30'] < 30)
    if low_count > len(rankings) // 2 and len(rankings) > 2:
        recs.append({'icon': 'lightning', 'color': '#0d6efd',
                     'text': 'Более половины привычек выполняются менее 30%. '
                             'Сфокусируйтесь на 2-3 ключевых привычках.'})

    if not recs:
        recs.append({'icon': 'check-circle', 'color': '#16a34a',
                     'text': 'Вы на правильном пути! Поддерживайте текущий ритм.'})

    return recs[:5]


def _forecast_goals(user_id):
    goals = Goal.query.filter_by(user_id=user_id, status='active').all()
    forecasts = []
    for g in goals:
        progress = g.progress
        if g.deadline:
            days_left = (g.deadline - date.today()).days
            if days_left > 0 and progress > 0:
                days_to_100 = int((100 - progress) / progress * 30) if progress > 0 else 999
                on_track = days_to_100 <= days_left
                forecasts.append({
                    'goal': g, 'progress': progress, 'days_left': days_left,
                    'on_track': on_track, 'estimated_days': days_to_100,
                })
            else:
                forecasts.append({
                    'goal': g, 'progress': progress, 'days_left': max(days_left, 0),
                    'on_track': days_left > 0, 'estimated_days': None,
                })
        else:
            forecasts.append({
                'goal': g, 'progress': progress, 'days_left': None,
                'on_track': True, 'estimated_days': None,
            })
    return forecasts


@reports_bp.route('/pdf')
@login_required
def generate_pdf():
    from fpdf import FPDF

    today = date.today()
    habits = current_user.habits.filter_by(is_archived=False).all()

    month_start = today.replace(day=1)
    month_stats = _get_period_stats(current_user.id, month_start, today)

    pdf = FPDF()
    pdf.add_page()

    font_dir = 'C:/Windows/Fonts/'
    try:
        pdf.add_font('DejaVu', '', font_dir + 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', font_dir + 'DejaVuSans-Bold.ttf', uni=True)
        font_name = 'DejaVu'
    except Exception:
        try:
            pdf.add_font('Arial', '', font_dir + 'arial.ttf', uni=True)
            pdf.add_font('Arial', 'B', font_dir + 'arialbd.ttf', uni=True)
            font_name = 'Arial'
        except Exception:
            font_name = 'Helvetica'

    pdf.set_font(font_name, 'B', 20)
    pdf.cell(0, 15, 'HabitFlow', new_x='LMARGIN', new_y='NEXT', align='C')

    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 8, f'Отчёт за {today.strftime("%B %Y")}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.cell(0, 8, f'Пользователь: {current_user.username}', new_x='LMARGIN', new_y='NEXT', align='C')
    pdf.ln(10)

    pdf.set_font(font_name, 'B', 14)
    pdf.cell(0, 10, 'Общая статистика', new_x='LMARGIN', new_y='NEXT')
    pdf.set_font(font_name, '', 11)
    pdf.cell(0, 8, f'Выполнено: {month_stats["total_done"]} из {month_stats["total_possible"]}',
             new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f'Процент выполнения: {month_stats["rate"]}%', new_x='LMARGIN', new_y='NEXT')
    pdf.cell(0, 8, f'Активных привычек: {len(habits)}', new_x='LMARGIN', new_y='NEXT')
    pdf.ln(5)

    if habits:
        pdf.set_font(font_name, 'B', 14)
        pdf.cell(0, 10, 'Привычки', new_x='LMARGIN', new_y='NEXT')

        pdf.set_font(font_name, 'B', 9)
        pdf.cell(70, 8, 'Название', border=1)
        pdf.cell(30, 8, '7 дней', border=1, align='C')
        pdf.cell(30, 8, '30 дней', border=1, align='C')
        pdf.cell(25, 8, 'Серия', border=1, align='C')
        pdf.cell(25, 8, 'Лучшая', border=1, align='C')
        pdf.ln()

        pdf.set_font(font_name, '', 9)
        for h in habits:
            name = h.name[:30]
            pdf.cell(70, 7, name, border=1)
            pdf.cell(30, 7, f'{h.completion_rate(7)}%', border=1, align='C')
            pdf.cell(30, 7, f'{h.completion_rate(30)}%', border=1, align='C')
            pdf.cell(25, 7, str(h.current_streak()), border=1, align='C')
            pdf.cell(25, 7, str(h.best_streak()), border=1, align='C')
            pdf.ln()

    pdf.ln(5)
    pdf.set_font(font_name, '', 8)
    pdf.cell(0, 8, f'Сгенерировано: {today.isoformat()}', new_x='LMARGIN', new_y='NEXT', align='R')

    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=habitflow_report_{today}.pdf'},
    )
