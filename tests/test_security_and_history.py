from datetime import date, timedelta
from unittest.mock import Mock

from flask import g

from app.extensions import bcrypt, db
from app.models.habit import Habit
from app.models.habit_log import HabitLog
from app.models.user import User
from app.models.goal import Goal
from app.services import create_notification


def login(client, email, password='password123'):
    g.pop('_login_user', None)
    return client.post('/auth/login', data={'email': email, 'password': password})


def test_schedule_changes_keep_past_dates(habit):
    today = date.today()
    old_day = today - timedelta(days=8)
    habit.change_schedule('weekly', [('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')[today.weekday()]], today - timedelta(days=7))
    db.session.add(HabitLog(habit_id=habit.id, date=old_day, completed=True))
    db.session.commit()
    db.session.expire_all()
    saved = db.session.get(Habit, habit.id)
    assert saved.is_scheduled_on(old_day)
    assert not saved.is_scheduled_on(today - timedelta(days=1))
    assert saved.is_scheduled_on(today)
    assert saved.completion_between(old_day, old_day) == (1, 1)


def test_same_day_schedule_changes_update_version(habit):
    habit.change_schedule('weekly', ['mon'])
    habit.change_schedule('weekly', ['fri'])
    db.session.commit()
    assert len([s for s in habit.schedules if s.effective_date == date.today()]) == 1
    assert habit.target_days == ['fri']


def test_password_reset_is_one_use_and_invalidates_token(client, app, user, monkeypatch):
    app.config.update(SMTP_HOST='smtp.invalid', SMTP_FROM='noreply@example.com', PUBLIC_BASE_URL='https://example.com')
    sent = []
    monkeypatch.setattr('app.routes.auth.send_email', lambda recipient, subject, body: sent.append(body) or True)
    user.generate_api_token()
    db.session.commit()
    response = client.post('/auth/forgot-password', data={'email': user.email})
    assert response.status_code == 302 and len(sent) == 1
    path = sent[0].split('https://example.com', 1)[1].splitlines()[0]
    assert client.get(path).status_code == 200
    response = client.post(path, data={'password': 'new-password-123', 'confirm_password': 'new-password-123'})
    assert response.status_code == 302
    db.session.refresh(user)
    assert bcrypt.check_password_hash(user.password_hash, 'new-password-123')
    assert user.api_token is None
    assert client.get(path).status_code == 302


def test_email_is_opt_in_and_delivery_failures_do_not_lose_notification(app, user, monkeypatch):
    app.config.update(SMTP_HOST='smtp.invalid', SMTP_FROM='noreply@example.com')
    send = Mock(return_value=False)
    monkeypatch.setattr('app.mail.send_email', send)
    create_notification(user.id, 'First')
    assert not send.called
    user.email_notifications = True
    db.session.commit()
    notification = create_notification(user.id, 'Second')
    assert send.call_count == 1
    assert db.session.get(type(notification), notification.id).title == 'Second'


def test_resend_api_uses_https_and_plain_text(app, monkeypatch):
    import json
    from app.mail import send_email
    app.config.update(EMAIL_PROVIDER='resend', RESEND_API_KEY='test-key', MAIL_FROM='noreply@example.com')
    captured = []
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
    def fake_open(request, timeout):
        captured.append(request)
        return Response()
    monkeypatch.setattr('app.mail.urlopen', fake_open)
    assert send_email('recipient@example.com', 'Subject', 'Message')
    assert captured[0].full_url == 'https://api.resend.com/emails'
    assert json.loads(captured[0].data)['text'] == 'Message'


def test_users_cannot_access_each_others_habits_or_admin(client, user, habit):
    other = User(email='other@example.com', username='other', password_hash=bcrypt.generate_password_hash('password123').decode())
    db.session.add(other)
    goal = Goal(user_id=user.id, title='Private goal')
    db.session.add(goal)
    db.session.commit()
    login(client, other.email)
    assert client.get(f'/habits/{habit.id}/edit').status_code == 404
    assert client.post(f'/tracking/check/{habit.id}').status_code == 404
    assert client.post(f'/habits/{habit.id}/delete').status_code == 404
    assert client.get('/admin/').status_code == 403
    assert client.post(f'/admin/users/{user.id}/toggle').status_code == 403
    assert client.post(f'/admin/users/{user.id}/delete').status_code == 403
    assert client.get(f'/goals/{goal.id}/edit').status_code == 404
    assert client.post(f'/goals/{goal.id}/complete').status_code == 404
    token = other.generate_api_token()
    db.session.commit()
    headers = {'Authorization': 'Bearer ' + token}
    assert client.get(f'/api/v1/habits/{habit.id}', headers=headers).status_code == 404
    assert client.delete(f'/api/v1/habits/{habit.id}', headers=headers).status_code == 404


def test_api_rejects_bad_dates_and_malformed_values(client, user, habit):
    token = user.generate_api_token()
    db.session.commit()
    headers = {'Authorization': 'Bearer ' + token}
    for body in ({'date': '2025-99-99'}, {'date': ['bad']}, []):
        assert client.post(f'/api/v1/habits/{habit.id}/check', headers=headers, json=body).status_code == 400
    for body in ({'name': ' '}, {'name': 'x' * 101}, {'name': 'Okay', 'category_id': -1}, {'name': 'Okay', 'frequency': 'weekly', 'target_days': ['noday']}):
        assert client.post('/api/v1/habits', headers=headers, json=body).status_code == 400


def test_password_reset_unavailable_without_mail(client, app, user):
    app.config.update(EMAIL_PROVIDER='smtp', SMTP_HOST='', SMTP_FROM='')
    response = client.post('/auth/forgot-password', data={'email': user.email}, follow_redirects=True)
    assert 'временно недоступно'.encode() in response.data


def test_new_user_sees_clear_next_steps(client, user):
    login(client, user.email)
    assert 'Создайте первую привычку'.encode() in client.get('/tracking/today').data
    assert 'Создайте цель и привяжите'.encode() in client.get('/goals/').data


def test_invalid_form_data_and_foreign_category_are_rejected(client, user, category):
    other = User(email='new@example.com', username='newuser', password_hash=bcrypt.generate_password_hash('password123').decode())
    db.session.add(other)
    db.session.commit()
    login(client, other.email)
    response = client.post('/habits/create', data={'name': 'x' * 101, 'frequency': 'daily',
                           'category_id': str(category.id), 'color': '#123456'})
    assert response.status_code == 200
    assert other.habits.count() == 0
    response = client.post('/goals/create', data={'title': 'Test', 'deadline': '2025-99-99'})
    assert response.status_code == 200
    assert other.goals.count() == 0
