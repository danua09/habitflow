from functools import wraps
from datetime import date, timedelta
import re
from flask import Blueprint, jsonify, request
from app.extensions import db
from app.models.user import User
from app.models.habit import Habit
from app.models.habit_log import HabitLog
from app.models.category import Category
from app.models.achievement import Achievement, UserAchievement

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def validate_habit(data, user, habit=None):
    if not isinstance(data, dict):
        return 'Ожидается JSON-объект'
    allowed = {'name', 'description', 'category_id', 'frequency', 'target_days', 'color', 'is_archived'}
    if set(data) - allowed:
        return 'Неизвестное поле'
    name = data.get('name', habit.name if habit else None)
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
        return 'Название должно содержать от 1 до 100 символов'
    description = data.get('description', habit.description if habit else '')
    if not isinstance(description, str) or len(description) > 500:
        return 'Описание должно быть строкой длиной до 500 символов'
    frequency = data.get('frequency', habit.frequency if habit else 'daily')
    days = data.get('target_days', habit.target_days if habit else []) or []
    if frequency not in ('daily', 'weekly'):
        return 'Недопустимая периодичность'
    if not isinstance(days, list) or any(not isinstance(d, str) or d not in ('mon','tue','wed','thu','fri','sat','sun') for d in days) or len(days) != len(set(days)):
        return 'Недопустимые дни недели'
    if frequency == 'weekly' and not days:
        return 'Выберите хотя бы один день недели'
    color = data.get('color', habit.color if habit else '#0d6efd')
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return 'Недопустимый цвет'
    if 'is_archived' in data and not isinstance(data['is_archived'], bool):
        return 'is_archived должен быть логическим значением'
    category = data.get('category_id', habit.category_id if habit else None)
    if category is not None and (type(category) is not int or not Category.query.filter_by(id=category, user_id=user.id).first()):
        return 'Категория не найдена'
    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Токен не предоставлен'}), 401
        token = auth[7:]
        user = User.query.filter_by(api_token=token).first()
        if not user or not user.is_active_user:
            return jsonify({'error': 'Неверный токен'}), 401
        return f(user, *args, **kwargs)
    return decorated


@api_bp.route('/auth/token', methods=['POST'])
def get_token():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('email'), str) or not isinstance(data.get('password'), str):
        return jsonify({'error': 'Требуются email и password'}), 400
    if len(data['password'].encode('utf-8')) > 72:
        return jsonify({'error': 'Неверные учётные данные'}), 401

    user = User.query.filter_by(email=data['email']).first()
    if not user:
        return jsonify({'error': 'Неверные учётные данные'}), 401

    from app.extensions import bcrypt
    if not bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Неверные учётные данные'}), 401

    if not user.is_active_user:
        return jsonify({'error': 'Аккаунт заблокирован'}), 403

    token = user.generate_api_token()
    db.session.commit()
    return jsonify({'token': token, 'user': _user_dict(user)})


@api_bp.route('/me')
@token_required
def me(user):
    return jsonify(_user_dict(user))


# --- Habits ---

@api_bp.route('/habits')
@token_required
def list_habits(user):
    archived = request.args.get('archived', '0') == '1'
    habits = user.habits.filter_by(is_archived=archived).order_by(Habit.created_at.desc()).all()
    return jsonify([_habit_dict(h) for h in habits])


@api_bp.route('/habits', methods=['POST'])
@token_required
def create_habit(user):
    data = request.get_json(silent=True)
    error = validate_habit(data, user)
    if error:
        return jsonify({'error': error}), 400

    category_id = data.get('category_id')
    habit = Habit(
        user_id=user.id,
        name=data['name'].strip(),
        description=data.get('description', ''),
        category_id=category_id,
        frequency=data.get('frequency', 'daily'),
        target_days=data.get('target_days', []),
        color=data.get('color', '#0d6efd'),
    )
    db.session.add(habit)
    db.session.commit()

    from app.services import check_achievements_on_habit_create
    check_achievements_on_habit_create(user.id)

    return jsonify(_habit_dict(habit)), 201


@api_bp.route('/habits/<int:habit_id>')
@token_required
def get_habit(user, habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()
    if not habit:
        return jsonify({'error': 'Привычка не найдена'}), 404
    return jsonify(_habit_dict(habit))


@api_bp.route('/habits/<int:habit_id>', methods=['PUT'])
@token_required
def update_habit(user, habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()
    if not habit:
        return jsonify({'error': 'Привычка не найдена'}), 404

    data = request.get_json(silent=True)
    error = validate_habit(data, user, habit)
    if error:
        return jsonify({'error': error}), 400
    if 'name' in data:
        habit.name = data['name'].strip()
    if 'description' in data:
        habit.description = data['description']
    if 'frequency' in data or 'target_days' in data:
        habit.change_schedule(data.get('frequency', habit.frequency), data.get('target_days', habit.target_days))
    if 'color' in data:
        habit.color = data['color']
    if 'category_id' in data:
        habit.category_id = data['category_id']
    if 'is_archived' in data:
        habit.is_archived = data['is_archived']

    db.session.commit()
    return jsonify(_habit_dict(habit))


@api_bp.route('/habits/<int:habit_id>', methods=['DELETE'])
@token_required
def delete_habit(user, habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()
    if not habit:
        return jsonify({'error': 'Привычка не найдена'}), 404
    db.session.delete(habit)
    db.session.commit()
    return jsonify({'message': 'Привычка удалена'})


# --- Tracking ---

@api_bp.route('/habits/<int:habit_id>/check', methods=['POST'])
@token_required
def check_habit(user, habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()
    if not habit:
        return jsonify({'error': 'Привычка не найдена'}), 404

    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Ожидается JSON-объект'}), 400
    check_date = date.today()
    if data.get('date'):
        try:
            check_date = date.fromisoformat(data['date'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Неверный формат даты'}), 400

    existing = HabitLog.query.filter_by(habit_id=habit.id, date=check_date).first()
    if existing:
        return jsonify({'message': 'Уже отмечено', 'streak': habit.current_streak()})

    log = HabitLog(habit_id=habit.id, date=check_date, completed=True)
    db.session.add(log)
    db.session.commit()

    from app.services import check_achievements_on_complete
    check_achievements_on_complete(user.id)

    return jsonify({'message': 'Отмечено', 'streak': habit.current_streak()}), 201


@api_bp.route('/habits/<int:habit_id>/uncheck', methods=['POST'])
@token_required
def uncheck_habit(user, habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=user.id).first()
    if not habit:
        return jsonify({'error': 'Привычка не найдена'}), 404

    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Ожидается JSON-объект'}), 400
    check_date = date.today()
    if data.get('date'):
        try:
            check_date = date.fromisoformat(data['date'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Неверный формат даты'}), 400

    log = HabitLog.query.filter_by(habit_id=habit.id, date=check_date).first()
    if log:
        db.session.delete(log)
        db.session.commit()

    return jsonify({'message': 'Отметка снята', 'streak': habit.current_streak()})


# --- Stats ---

@api_bp.route('/stats')
@token_required
def stats(user):
    today_date = date.today()
    habits = user.habits.filter_by(is_archived=False).all()
    day_map = {0: 'mon', 1: 'tue', 2: 'wed', 3: 'thu', 4: 'fri', 5: 'sat', 6: 'sun'}
    current_day = day_map[today_date.weekday()]

    today_total = 0
    today_completed = 0
    habit_stats = []

    for h in habits:
        is_today = h.frequency == 'daily' or (h.frequency == 'weekly' and current_day in (h.target_days or []))
        if is_today:
            today_total += 1
            if h.is_completed_on(today_date):
                today_completed += 1
        habit_stats.append({
            'id': h.id,
            'name': h.name,
            'streak': h.current_streak(),
            'best_streak': h.best_streak(),
            'rate_7': h.completion_rate(7),
            'rate_30': h.completion_rate(30),
        })

    total_logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == user.id, HabitLog.completed == True
    ).count()

    return jsonify({
        'today': {'completed': today_completed, 'total': today_total},
        'total_completions': total_logs,
        'habits': habit_stats,
    })


# --- Achievements ---

@api_bp.route('/achievements')
@token_required
def achievements(user):
    all_achievements = Achievement.query.all()
    earned_ids = {ua.achievement_id for ua in
                  UserAchievement.query.filter_by(user_id=user.id).all()}
    result = []
    for a in all_achievements:
        result.append({
            'id': a.id, 'code': a.code, 'name': a.name,
            'description': a.description, 'icon': a.icon, 'color': a.color,
            'earned': a.id in earned_ids,
        })
    return jsonify(result)


# --- Categories ---

@api_bp.route('/categories')
@token_required
def list_categories(user):
    cats = user.categories.order_by(Category.name).all()
    return jsonify([{'id': c.id, 'name': c.name, 'icon': c.icon, 'color': c.color} for c in cats])


def _user_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'bio': user.bio or '',
        'is_public': user.is_public,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


def _habit_dict(habit):
    return {
        'id': habit.id,
        'name': habit.name,
        'description': habit.description,
        'frequency': habit.frequency,
        'target_days': habit.target_days or [],
        'color': habit.color,
        'is_archived': habit.is_archived,
        'category_id': habit.category_id,
        'streak': habit.current_streak(),
        'best_streak': habit.best_streak(),
        'rate_30': habit.completion_rate(30),
        'created_at': habit.created_at.isoformat() if habit.created_at else None,
    }
