from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.template import HabitTemplate, TemplateHabit
from app.models.habit import Habit
from app.models.category import Category

templates_bp = Blueprint('templates', __name__, url_prefix='/templates')


@templates_bp.route('/')
@login_required
def index():
    public_templates = HabitTemplate.query.filter_by(is_public=True).all()
    my_templates = HabitTemplate.query.filter_by(
        created_by=current_user.id, is_public=False
    ).all()

    return render_template('templates/index.html',
                           public_templates=public_templates,
                           my_templates=my_templates)


@templates_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        icon = request.form.get('icon', 'collection').strip()
        color = request.form.get('color', '#f59e0b')
        is_public = 'is_public' in request.form and current_user.is_moderator

        if not name:
            flash('Название обязательно.', 'danger')
            return redirect(url_for('templates.create'))

        habit_names = request.form.getlist('habit_name')
        habit_frequencies = request.form.getlist('habit_frequency')
        for i, h_name in enumerate(habit_names):
            freq = habit_frequencies[i] if i < len(habit_frequencies) else 'daily'
            days = request.form.getlist(f'habit_days_{i}')
            if h_name.strip() and (freq not in ('daily', 'weekly') or
                                   (freq == 'weekly' and (not days or any(d not in ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun') for d in days)))):
                flash('Для привычки по дням недели выберите дни.', 'danger')
                return redirect(url_for('templates.create'))

        template = HabitTemplate(
            name=name, description=description, icon=icon,
            color=color, is_public=is_public, created_by=current_user.id,
        )
        db.session.add(template)
        db.session.flush()

        habit_colors = request.form.getlist('habit_color')

        for i, h_name in enumerate(habit_names):
            h_name = h_name.strip()
            if not h_name:
                continue
            freq = habit_frequencies[i] if i < len(habit_frequencies) else 'daily'
            col = habit_colors[i] if i < len(habit_colors) else '#0d6efd'
            item = TemplateHabit(
                template_id=template.id, name=h_name,
                frequency=freq, color=col,
                target_days=request.form.getlist(f'habit_days_{i}') if freq == 'weekly' else [],
            )
            db.session.add(item)

        db.session.commit()
        flash('Шаблон создан!', 'success')
        return redirect(url_for('templates.index'))

    return render_template('templates/form.html', title='Новый шаблон', template=None)


@templates_bp.route('/<int:template_id>')
@login_required
def view(template_id):
    template = HabitTemplate.query.get_or_404(template_id)
    if not template.is_public and template.created_by != current_user.id:
        flash('Шаблон не найден.', 'danger')
        return redirect(url_for('templates.index'))

    habits = template.items.all()
    return render_template('templates/view.html', template=template, habits=habits)


@templates_bp.route('/<int:template_id>/apply', methods=['POST'])
@login_required
def apply(template_id):
    template = HabitTemplate.query.get_or_404(template_id)
    if not template.is_public and template.created_by != current_user.id:
        flash('Шаблон не найден.', 'danger')
        return redirect(url_for('templates.index'))

    default_category = current_user.categories.first()
    items = template.items.all()
    created = 0

    for item in items:
        habit = Habit(
            user_id=current_user.id,
            category_id=default_category.id if default_category else None,
            name=item.name,
            description=item.description,
            frequency=item.frequency,
            target_days=item.target_days,
            color=item.color,
        )
        db.session.add(habit)
        created += 1

    db.session.commit()

    from app.services import check_achievements_on_habit_create
    check_achievements_on_habit_create(current_user.id)

    flash(f'Добавлено {created} привычек из шаблона «{template.name}»!', 'success')
    return redirect(url_for('habits.index'))


@templates_bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete(template_id):
    template = HabitTemplate.query.get_or_404(template_id)
    if template.created_by != current_user.id and not current_user.is_admin:
        flash('Нет прав для удаления.', 'danger')
        return redirect(url_for('templates.index'))

    db.session.delete(template)
    db.session.commit()
    flash('Шаблон удалён.', 'info')
    return redirect(url_for('templates.index'))
