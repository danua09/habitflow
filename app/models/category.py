from app.extensions import db


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(50), default='folder')
    color = db.Column(db.String(7), default='#6c757d')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    habits = db.relationship('Habit', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'
