from datetime import datetime, timezone, date
from app.extensions import db

goal_habits = db.Table(
    'goal_habits',
    db.Column('goal_id', db.Integer, db.ForeignKey('goals.id'), primary_key=True),
    db.Column('habit_id', db.Integer, db.ForeignKey('habits.id'), primary_key=True),
)


class Goal(db.Model):
    __tablename__ = 'goals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, default='')
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    habits = db.relationship('Habit', secondary=goal_habits, backref='goals', lazy='dynamic')

    @property
    def progress(self):
        habits = self.habits.all()
        if not habits:
            return 0
        total = sum(h.completion_rate(30) for h in habits)
        return round(total / len(habits), 1)

    @property
    def is_overdue(self):
        return self.deadline and self.deadline < date.today() and self.status == 'active'

    def __repr__(self):
        return f'<Goal {self.title}>'
