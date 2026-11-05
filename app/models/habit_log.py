from datetime import datetime, timezone
from app.extensions import db


class HabitLog(db.Model):
    __tablename__ = 'habit_logs'

    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habits.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    completed = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('habit_id', 'date', name='uq_habit_date'),
    )

    def __repr__(self):
        return f'<HabitLog habit={self.habit_id} date={self.date}>'
