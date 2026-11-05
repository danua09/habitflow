from datetime import datetime, timezone, date, timedelta
from app.extensions import db


class Habit(db.Model):
    __tablename__ = 'habits'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    frequency = db.Column(db.String(20), nullable=False, default='daily')
    color = db.Column(db.String(7), default='#0d6efd')
    is_archived = db.Column(db.Boolean, default=False)
    target_days = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    logs = db.relationship('HabitLog', backref='habit', lazy='dynamic', cascade='all, delete-orphan')

    def is_completed_on(self, check_date):
        from app.models.habit_log import HabitLog
        return self.logs.filter_by(date=check_date, completed=True).first() is not None

    def current_streak(self):
        today = date.today()
        streak = 0
        current = today
        while True:
            if self.is_completed_on(current):
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        return streak

    def best_streak(self):
        logs = (self.logs
                .filter_by(completed=True)
                .order_by(db.asc('date'))
                .all())
        if not logs:
            return 0
        best = 1
        current = 1
        for i in range(1, len(logs)):
            if (logs[i].date - logs[i - 1].date).days == 1:
                current += 1
                best = max(best, current)
            else:
                current = 1
        return best

    def completion_rate(self, days=30):
        today = date.today()
        start = today - timedelta(days=days - 1)
        from app.models.habit_log import HabitLog
        total = self.logs.filter(
            HabitLog.date >= start,
            HabitLog.date <= today,
            HabitLog.completed == True,
        ).count()
        return round(total / days * 100, 1)

    def __repr__(self):
        return f'<Habit {self.name}>'
