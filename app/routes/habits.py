from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.habit import Habit
from app.models.category import Category
from app.forms import HabitForm, CategoryForm

habits_bp = Blueprint('habits', __name__, url_prefix='/habits')


@habits_bp.route('/')
@login_required
def index():
    category_id = request.args.get('category', type=int)
    show_archived = request.args.get('archived', '0') == '1'

    query = current_user.habits
    if category_id:
        query = query.filter_by(category_id=category_id)
    query = query.filter_by(is_archived=show_archived)
    habits = query.order_by(Habit.created_at.desc()).all()

    categories = current_user.categories.order_by(Category.name).all()
    return render_template('habits/index.html', habits=habits, categories=categories,
                           current_category=category_id, show_archived=show_archived)


@habits_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = HabitForm()
    categories = current_user.categories.order_by(Category.name).all()
    form.category_id.choices = [(0, '— Без категории —')] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        habit = Habit(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            category_id=form.category_id.data or None,
            frequency=form.frequency.data,
            target_days=form.target_days.data if form.frequency.data == 'weekly' else [],
            color=form.color.data,
        )
        db.session.add(habit)
        db.session.commit()

        from app.services import check_achievements_on_habit_create
        check_achievements_on_habit_create(current_user.id)

        flash('Привычка создана!', 'success')
        return redirect(url_for('habits.index'))

    return render_template('habits/form.html', form=form, title='Новая привычка')


@habits_bp.route('/<int:habit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    form = HabitForm(obj=habit)
    categories = current_user.categories.order_by(Category.name).all()
    form.category_id.choices = [(0, '— Без категории —')] + [(c.id, c.name) for c in categories]

    if form.validate_on_submit():
        habit.name = form.name.data
        habit.description = form.description.data
        habit.category_id = form.category_id.data or None
        habit.change_schedule(form.frequency.data, form.target_days.data)
        habit.color = form.color.data
        db.session.commit()
        flash('Привычка обновлена!', 'success')
        return redirect(url_for('habits.index'))

    if request.method == 'GET':
        form.target_days.data = habit.target_days or []

    return render_template('habits/form.html', form=form, title='Редактирование', habit=habit)


@habits_bp.route('/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    db.session.delete(habit)
    db.session.commit()
    flash('Привычка удалена.', 'info')
    return redirect(url_for('habits.index'))


@habits_bp.route('/<int:habit_id>/archive', methods=['POST'])
@login_required
def archive(habit_id):
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.is_archived = not habit.is_archived
    db.session.commit()
    action = 'архивирована' if habit.is_archived else 'восстановлена'
    flash(f'Привычка {action}.', 'info')
    return redirect(url_for('habits.index'))


@habits_bp.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        cat = Category(
            name=form.name.data,
            icon=form.icon.data,
            color=form.color.data,
            user_id=current_user.id,
        )
        db.session.add(cat)
        db.session.commit()
        flash('Категория создана!', 'success')
        return redirect(url_for('habits.categories'))

    cats = current_user.categories.order_by(Category.name).all()
    return render_template('habits/categories.html', form=form, categories=cats)


@habits_bp.route('/categories/<int:cat_id>/delete', methods=['POST'])
@login_required
def delete_category(cat_id):
    cat = Category.query.filter_by(id=cat_id, user_id=current_user.id).first_or_404()
    Habit.query.filter_by(category_id=cat.id).update({'category_id': None})
    db.session.delete(cat)
    db.session.commit()
    flash('Категория удалена.', 'info')
    return redirect(url_for('habits.categories'))
