from datetime import date
from app.extensions import db
from app.models.achievement import Achievement, UserAchievement
from app.models.notification import Notification
from app.models.habit import Habit
from app.models.habit_log import HabitLog


ACHIEVEMENT_DEFINITIONS = [
    {'code': 'streak_3', 'name': 'Три дня подряд', 'description': 'Выполняйте привычку 3 дня подряд', 'icon': 'fire', 'color': '#f59e0b'},
    {'code': 'streak_7', 'name': 'Неделя силы', 'description': 'Серия из 7 дней подряд', 'icon': 'fire', 'color': '#f97316'},
    {'code': 'streak_30', 'name': 'Месяц дисциплины', 'description': 'Серия из 30 дней подряд', 'icon': 'fire', 'color': '#ef4444'},
    {'code': 'streak_100', 'name': 'Стодневный марафон', 'description': 'Невероятная серия из 100 дней', 'icon': 'fire', 'color': '#dc2626'},
    {'code': 'total_10', 'name': 'Первые шаги', 'description': 'Выполните привычки 10 раз суммарно', 'icon': 'star', 'color': '#fbbf24'},
    {'code': 'total_50', 'name': 'На пути к успеху', 'description': '50 выполнений — отличный результат!', 'icon': 'star-fill', 'color': '#f59e0b'},
    {'code': 'total_100', 'name': 'Сотня!', 'description': '100 выполнений привычек', 'icon': 'award', 'color': '#d97706'},
    {'code': 'total_500', 'name': 'Легенда', 'description': '500 выполнений — вы легенда!', 'icon': 'gem', 'color': '#b45309'},
    {'code': 'first_habit', 'name': 'Начало пути', 'description': 'Создайте свою первую привычку', 'icon': 'plus-circle', 'color': '#16a34a'},
    {'code': 'five_habits', 'name': 'Коллекционер', 'description': 'Создайте 5 привычек', 'icon': 'collection', 'color': '#0d9488'},
    {'code': 'first_goal', 'name': 'Целеустремлённый', 'description': 'Создайте свою первую цель', 'icon': 'bullseye', 'color': '#8b5cf6'},
    {'code': 'goal_completed', 'name': 'Цель достигнута', 'description': 'Выполните цель', 'icon': 'trophy', 'color': '#eab308'},
    {'code': 'all_today', 'name': 'Идеальный день', 'description': 'Выполните все привычки за день', 'icon': 'check-circle', 'color': '#22c55e'},
]


def seed_achievements():
    for defn in ACHIEVEMENT_DEFINITIONS:
        existing = Achievement.query.filter_by(code=defn['code']).first()
        if not existing:
            db.session.add(Achievement(**defn))
    db.session.commit()


def grant_achievement(user_id, code):
    achievement = Achievement.query.filter_by(code=code).first()
    if not achievement:
        return None

    existing = UserAchievement.query.filter_by(
        user_id=user_id, achievement_id=achievement.id
    ).first()
    if existing:
        return None

    ua = UserAchievement(user_id=user_id, achievement_id=achievement.id)
    db.session.add(ua)

    notification = Notification(
        user_id=user_id,
        type='achievement',
        title=f'Новое достижение: {achievement.name}!',
        message=achievement.description,
        link='/achievements',
    )
    db.session.add(notification)
    db.session.commit()
    _email_notification(notification)
    return ua


def log_activity(user_id, action, description=''):
    from app.models.social import ActivityLog
    db.session.add(ActivityLog(user_id=user_id, action=action, description=description))


def check_achievements_on_complete(user_id):
    total_logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == user_id,
        HabitLog.completed == True,
    ).count()

    if total_logs >= 10:
        grant_achievement(user_id, 'total_10')
    if total_logs >= 50:
        grant_achievement(user_id, 'total_50')
    if total_logs >= 100:
        grant_achievement(user_id, 'total_100')
    if total_logs >= 500:
        grant_achievement(user_id, 'total_500')

    habits = Habit.query.filter_by(user_id=user_id, is_archived=False).all()
    for habit in habits:
        streak = habit.current_streak()
        if streak >= 3:
            grant_achievement(user_id, 'streak_3')
        if streak >= 7:
            grant_achievement(user_id, 'streak_7')
        if streak >= 30:
            grant_achievement(user_id, 'streak_30')
        if streak >= 100:
            grant_achievement(user_id, 'streak_100')

    today_date = date.today()
    day_map = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
    current_day = day_map[today_date.weekday()]

    today_habits = []
    for h in habits:
        if h.frequency == 'daily' or (h.frequency == 'weekly' and current_day in (h.target_days or [])):
            today_habits.append(h)

    if today_habits and all(h.is_completed_on(today_date) for h in today_habits):
        grant_achievement(user_id, 'all_today')


def check_achievements_on_habit_create(user_id):
    count = Habit.query.filter_by(user_id=user_id).count()
    if count >= 1:
        grant_achievement(user_id, 'first_habit')
    if count >= 5:
        grant_achievement(user_id, 'five_habits')


def check_achievements_on_goal_create(user_id):
    from app.models.goal import Goal
    count = Goal.query.filter_by(user_id=user_id).count()
    if count >= 1:
        grant_achievement(user_id, 'first_goal')


def check_achievements_on_goal_complete(user_id):
    grant_achievement(user_id, 'goal_completed')


def create_notification(user_id, title, message='', type='system', link=None):
    n = Notification(user_id=user_id, type=type, title=title, message=message, link=link)
    db.session.add(n)
    db.session.commit()
    _email_notification(n)
    return n


def _email_notification(notification):
    from app.models.user import User
    from app.mail import mail_configured, send_email
    user = db.session.get(User, notification.user_id)
    if user and user.is_active_user and user.email_notifications and mail_configured():
        send_email(user.email, 'Уведомление HabitFlow', f'{notification.title}\n\n{notification.message or ""}')


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()
