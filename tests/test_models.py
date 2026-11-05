from datetime import date, timedelta
from app.extensions import db
from app.models.habit_log import HabitLog
from app.models.user import ROLE_USER, ROLE_ADMIN


class TestUserModel:

    def test_user_creation(self, user):
        assert user.id is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.role == ROLE_USER

    def test_user_roles(self, user, admin):
        assert not user.is_admin
        assert not user.is_moderator
        assert admin.is_admin
        assert admin.is_moderator

    def test_role_display(self, user, admin):
        assert user.role_display == 'Пользователь'
        assert admin.role_display == 'Администратор'

    def test_generate_api_token(self, user):
        token = user.generate_api_token()
        assert token is not None
        assert len(token) == 64
        assert user.api_token == token


class TestHabitModel:

    def test_habit_creation(self, habit):
        assert habit.id is not None
        assert habit.name == 'Утренняя зарядка'
        assert habit.frequency == 'daily'
        assert not habit.is_archived

    def test_is_completed_on(self, habit):
        today = date.today()
        assert not habit.is_completed_on(today)
        db.session.add(HabitLog(habit_id=habit.id, date=today, completed=True))
        db.session.flush()
        assert habit.is_completed_on(today)

    def test_current_streak(self, habit):
        assert habit.current_streak() == 0
        today = date.today()
        for i in range(3):
            db.session.add(HabitLog(habit_id=habit.id, date=today - timedelta(days=i), completed=True))
        db.session.flush()
        assert habit.current_streak() == 3

    def test_best_streak(self, habit):
        today = date.today()
        for i in range(5):
            db.session.add(HabitLog(habit_id=habit.id, date=today - timedelta(days=i), completed=True))
        db.session.add(HabitLog(habit_id=habit.id, date=today - timedelta(days=10), completed=True))
        db.session.add(HabitLog(habit_id=habit.id, date=today - timedelta(days=11), completed=True))
        db.session.flush()
        assert habit.best_streak() == 5

    def test_completion_rate(self, habit):
        today = date.today()
        for i in range(7):
            db.session.add(HabitLog(habit_id=habit.id, date=today - timedelta(days=i), completed=True))
        db.session.flush()
        rate = habit.completion_rate(7)
        assert rate == 100.0
