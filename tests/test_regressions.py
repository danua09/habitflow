from datetime import date, datetime, timedelta, timezone

from flask import g

from app.extensions import db
from app.models.achievement import UserAchievement, Achievement
from app.models.goal import Goal
from app.models.habit_log import HabitLog
from app.models.notification import Notification
from app.models.social import ActivityLog, Challenge, Friendship
from app.models.template import HabitTemplate, TemplateHabit
from app.models.user import User


def login(client, email, password='password123'):
    return client.post('/auth/login', data={'email': email, 'password': password})


def clear_login_cache():
    g.pop('_login_user', None)


def test_weekly_rate_and_streak_respect_schedule(habit):
    today = date.today()
    days = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
    habit.frequency = 'weekly'
    habit.target_days = [days[today.weekday()]]
    for offset in (0, 7, 14):
        db.session.add(HabitLog(habit_id=habit.id, date=today - timedelta(days=offset)))
    db.session.flush()
    assert habit.completion_rate(7) == 100
    assert habit.current_streak() == 3
    assert habit.best_streak() == 3


def test_current_streak_remains_until_today_is_over(habit):
    db.session.add(HabitLog(habit_id=habit.id, date=date.today() - timedelta(days=1)))
    db.session.flush()
    assert habit.current_streak() == 1


def test_goal_progress_starts_at_goal_creation(habit, user):
    today = date.today()
    goal = Goal(user_id=user.id, title='Goal', created_at=datetime.now(timezone.utc) - timedelta(days=1))
    goal.habits.append(habit)
    db.session.add_all([goal, HabitLog(habit_id=habit.id, date=today),
                        HabitLog(habit_id=habit.id, date=today - timedelta(days=2))])
    db.session.flush()
    assert goal.progress == 50


def test_weekly_form_requires_days(client, user):
    login(client, user.email)
    response = client.post('/habits/create', data={'name': 'Exercise', 'frequency': 'weekly', 'category_id': '0', 'color': '#123456'})
    assert 'Выберите хотя бы один день недели'.encode() in response.data
    assert user.habits.count() == 0


def test_login_rejects_external_next(client, user):
    response = client.post('/auth/login?next=https://example.com', data={'email': user.email, 'password': 'password123'})
    assert response.headers['Location'].endswith('/tracking/today')


def test_blocked_session_loses_access(client, user):
    login(client, user.email)
    user.is_active_user = False
    db.session.commit()
    clear_login_cache()
    assert client.get('/tracking/today').status_code == 302


def test_api_rejects_invalid_habit_data(client, user):
    token = user.generate_api_token()
    db.session.commit()
    headers = {'Authorization': 'Bearer ' + token}
    for data in ({'name': 'Test', 'frequency': 'wrong'}, {'name': 'Test', 'frequency': 'weekly'},
                 {'name': 'Test', 'category_id': 9999}, {'name': 'Test', 'target_days': [1]}):
        assert client.post('/api/v1/habits', json=data, headers=headers).status_code == 400
    assert user.habits.count() == 0


def test_admin_deletes_user_with_related_data(client, user, admin, habit):
    habit.change_schedule('weekly', ['mon'])
    template = HabitTemplate(name='Template', created_by=user.id)
    db.session.add(template)
    db.session.flush()
    goal = Goal(user_id=user.id, title='Goal')
    db.session.add(goal)
    goal.habits.append(habit)
    db.session.add_all([goal, HabitLog(habit_id=habit.id, date=date.today()),
                        Notification(user_id=user.id, title='Notice'),
                        UserAchievement(user_id=user.id, achievement_id=Achievement.query.first().id),
                        ActivityLog(user_id=user.id, action='check'),
                        Friendship(user_id=user.id, friend_id=admin.id),
                        Challenge(creator_id=user.id, opponent_id=admin.id, habit_name='Test'),
                        TemplateHabit(template_id=template.id, name='Test')])
    db.session.commit()
    user_id = user.id
    login(client, admin.email, 'admin123')
    response = client.post(f'/admin/users/{user_id}/delete')
    assert response.status_code == 302
    assert db.session.get(User, user_id) is None
    assert Notification.query.filter_by(user_id=user_id).count() == 0


def test_weekly_template_copies_selected_days(client, user):
    login(client, user.email)
    response = client.post('/templates/create', data={'name': 'Plan', 'habit_name': 'Walk',
                           'habit_frequency': 'weekly', 'habit_color': '#123456',
                           'habit_days_0': ['mon', 'fri']})
    assert response.status_code == 302
    template = HabitTemplate.query.filter_by(name='Plan').one()
    assert template.items.first().target_days == ['mon', 'fri']
    client.post(f'/templates/{template.id}/apply')
    assert user.habits.filter_by(name='Walk').first().target_days == ['mon', 'fri']


def test_challenges_are_removed_from_social_section(client, user):
    login(client, user.email)
    response = client.get('/social/')
    assert response.status_code == 200
    assert 'челлендж'.encode() not in response.data.lower()
    assert client.get('/social/challenge/create/1').status_code == 404
    assert client.get('/social/challenge/1').status_code == 404
    assert client.post('/social/challenge/1/accept').status_code == 404
