from datetime import datetime, timezone
from app.extensions import db


class HabitTemplate(db.Model):
    __tablename__ = 'habit_templates'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    icon = db.Column(db.String(50), default='collection')
    color = db.Column(db.String(7), default='#f59e0b')
    is_public = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    items = db.relationship('TemplateHabit', backref='template',
                            lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('User', backref='created_templates')

    def __repr__(self):
        return f'<HabitTemplate {self.name}>'


class TemplateHabit(db.Model):
    __tablename__ = 'template_habits'

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('habit_templates.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, default='')
    frequency = db.Column(db.String(20), default='daily')
    target_days = db.Column(db.JSON, default=list)
    color = db.Column(db.String(7), default='#0d6efd')

    def __repr__(self):
        return f'<TemplateHabit {self.name}>'
