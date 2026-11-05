from datetime import datetime, timezone
from app.extensions import db


class Friendship(db.Model):
    __tablename__ = 'friendships'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', foreign_keys=[user_id], backref='sent_requests')
    friend = db.relationship('User', foreign_keys=[friend_id], backref='received_requests')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='uq_friendship'),
    )


class Challenge(db.Model):
    __tablename__ = 'challenges'

    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opponent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    habit_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    duration_days = db.Column(db.Integer, default=7)
    status = db.Column(db.String(20), default='pending')
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_challenges')
    opponent = db.relationship('User', foreign_keys=[opponent_id], backref='received_challenges')


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref='activities')
