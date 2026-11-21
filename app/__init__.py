import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from app.config import Config
from app.extensions import db, login_manager, bcrypt, migrate, csrf


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    if not app.testing and os.environ.get('FLASK_ENV') == 'production':
        secret = app.config.get('SECRET_KEY') or ''
        if secret == 'dev-secret-key' or len(secret) < 32:
            raise RuntimeError('В рабочем окружении задайте SECRET_KEY длиной не менее 32 символов.')

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.models import (User, Category, Habit, HabitLog, Goal,
                            Achievement, UserAchievement, Notification,
                            HabitTemplate, TemplateHabit,
                            Friendship, Challenge, ActivityLog)

    from app.routes.auth import auth_bp
    from app.routes.habits import habits_bp
    from app.routes.tracking import tracking_bp
    from app.routes.stats import stats_bp
    from app.routes.goals import goals_bp
    from app.routes.profile import profile_bp
    from app.routes.admin import admin_bp
    from app.routes.achievements import achievements_bp
    from app.routes.notifications import notifications_bp
    from app.routes.templates import templates_bp
    from app.routes.api import api_bp
    from app.routes.social import social_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(achievements_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(social_bp)
    app.register_blueprint(reports_bp)

    csrf.exempt(api_bp)
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    @app.context_processor
    def inject_notification_count():
        from flask_login import current_user
        from app.mail import mail_configured
        if current_user.is_authenticated:
            from app.services import get_unread_count
            return {'unread_notifications': get_unread_count(current_user.id), 'mail_available': mail_configured()}
        return {'unread_notifications': 0, 'mail_available': mail_configured()}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'no-referrer')
        return response

    @app.route('/')
    def index():
        from flask import redirect, url_for
        from flask_login import current_user
        if current_user.is_authenticated:
            return redirect(url_for('tracking.today'))
        return redirect(url_for('auth.login'))

    return app
