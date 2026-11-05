from datetime import datetime, timezone
from app.extensions import db


class Achievement(db.Model):
    __tablename__ = 'achievements'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), default='')
    icon = db.Column(db.String(50), default='trophy')
    color = db.Column(db.String(7), default='#f59e0b')

    user_achievements = db.relationship('UserAchievement', backref='achievement',
                                         lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Achievement {self.code}>'


class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )

    def __repr__(self):
        return f'<UserAchievement user={self.user_id} achievement={self.achievement_id}>'
