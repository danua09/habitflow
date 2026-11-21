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
    schedules = db.relationship('HabitSchedule', backref='habit', lazy='select',
                                cascade='all, delete-orphan', order_by='HabitSchedule.effective_date')

    def is_completed_on(self, check_date):
        from app.models.habit_log import HabitLog
        return self.logs.filter_by(date=check_date, completed=True).first() is not None

    def is_scheduled_on(self, check_date):
        days = ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun')
        versions = [s for s in self.schedules if s.effective_date <= check_date]
        schedule = versions[-1] if versions else None
        frequency = schedule.frequency if schedule else self.frequency
        target_days = schedule.target_days if schedule else self.target_days
        return frequency == 'daily' or (
            frequency == 'weekly' and days[check_date.weekday()] in (target_days or [])
        )

    def change_schedule(self, frequency, target_days, effective_date=None):
        effective_date = effective_date or date.today()
        target_days = list(target_days or []) if frequency == 'weekly' else []
        if self.frequency == frequency and (self.target_days or []) == target_days:
            return
        if not self.schedules:
            self.schedules.append(HabitSchedule(effective_date=self._start_date(),
                                  frequency=self.frequency, target_days=list(self.target_days or [])))
        version = next((s for s in self.schedules if s.effective_date == effective_date), None)
        if version:
            version.frequency = frequency
            version.target_days = target_days
        else:
            self.schedules.append(HabitSchedule(effective_date=effective_date,
                                               frequency=frequency, target_days=target_days))
        self.frequency = frequency
        self.target_days = target_days

    def _start_date(self):
        return self.created_at.date() if self.created_at else date.today()

    def completion_between(self, start, end):
        from app.models.habit_log import HabitLog
        start = max(start, self._start_date())
        if end < start:
            return (0, 0)
        scheduled = {start + timedelta(days=i) for i in range((end - start).days + 1)
                     if self.is_scheduled_on(start + timedelta(days=i))}
        completed = {log.date for log in self.logs.filter(
            HabitLog.date >= start, HabitLog.date <= end, HabitLog.completed.is_(True)).all()}
        return len(scheduled & completed), len(scheduled)

    def current_streak(self):
        today = date.today()
        start = self._start_date()
        completed = {log.date for log in self.logs.filter_by(completed=True).all()}
        current = today
        if current not in completed:
            current -= timedelta(days=1)
        streak = 0
        while current >= start:
            if self.is_scheduled_on(current):
                if current not in completed:
                    break
                streak += 1
            current -= timedelta(days=1)
        return streak

    def best_streak(self):
        logs = (self.logs
                .filter_by(completed=True)
                .order_by(db.asc('date'))
                .all())
        if not logs:
            return 0
        completed = {log.date for log in logs if self._start_date() <= log.date <= date.today()}
        if not completed:
            return 0
        best = current = 0
        day = self._start_date()
        while day <= max(completed):
            if self.is_scheduled_on(day):
                current = current + 1 if day in completed else 0
                best = max(best, current)
            day += timedelta(days=1)
        return best

    def completion_rate(self, days=30):
        today = date.today()
        if days <= 0:
            return 0
        done, scheduled = self.completion_between(today - timedelta(days=days - 1), today)
        return round(done / scheduled * 100, 1) if scheduled else 0

    def __repr__(self):
        return f'<Habit {self.name}>'


class HabitSchedule(db.Model):
    __tablename__ = 'habit_schedules'
    id = db.Column(db.Integer, primary_key=True)
    habit_id = db.Column(db.Integer, db.ForeignKey('habits.id'), nullable=False)
    effective_date = db.Column(db.Date, nullable=False)
    frequency = db.Column(db.String(20), nullable=False)
    target_days = db.Column(db.JSON, nullable=False, default=list)
    __table_args__ = (db.UniqueConstraint('habit_id', 'effective_date', name='uq_habit_schedule_date'),)
