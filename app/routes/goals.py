from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.goal import Goal
from app.models.habit import Habit
from app.forms import GoalForm

goals_bp = Blueprint('goals', __name__, url_prefix='/goals')


@goals_bp.route('/')
@login_required
def index():
    active = current_user.goals.filter_by(status='active').order_by(Goal.deadline.asc().nulls_last()).all()
    completed = current_user.goals.filter_by(status='completed').order_by(Goal.updated_at.desc()).all()
    return render_template('goals/index.html', active_goals=active, completed_goals=completed)


@goals_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = GoalForm()
    habits = current_user.habits.filter_by(is_archived=False).order_by(Habit.name).all()
    form.habit_ids.choices = [(h.id, h.name) for h in habits]

    if form.validate_on_submit():
        goal = Goal(
            user_id=current_user.id,
            title=form.title.data,
            description=form.description.data,
            deadline=form.deadline.data,
        )
        db.session.add(goal)
        db.session.flush()

        selected = Habit.query.filter(
            Habit.id.in_(form.habit_ids.data),
            Habit.user_id == current_user.id,
        ).all()
        for h in selected:
            goal.habits.append(h)

        db.session.commit()

        from app.services import check_achievements_on_goal_create
        check_achievements_on_goal_create(current_user.id)

        flash('Цель создана!', 'success')
        return redirect(url_for('goals.index'))

    return render_template('goals/form.html', form=form, title='Новая цель')


@goals_bp.route('/<int:goal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    form = GoalForm(obj=goal)
    habits = current_user.habits.filter_by(is_archived=False).order_by(Habit.name).all()
    form.habit_ids.choices = [(h.id, h.name) for h in habits]

    if form.validate_on_submit():
        goal.title = form.title.data
        goal.description = form.description.data
        goal.deadline = form.deadline.data

        goal.habits = []
        selected = Habit.query.filter(
            Habit.id.in_(form.habit_ids.data),
            Habit.user_id == current_user.id,
        ).all()
        for h in selected:
            goal.habits.append(h)

        db.session.commit()
        flash('Цель обновлена!', 'success')
        return redirect(url_for('goals.index'))

    if form.habit_ids.data is None:
        form.habit_ids.data = [h.id for h in goal.habits.all()]

    return render_template('goals/form.html', form=form, title='Редактирование', goal=goal)


@goals_bp.route('/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash('Цель удалена.', 'info')
    return redirect(url_for('goals.index'))


@goals_bp.route('/<int:goal_id>/complete', methods=['POST'])
@login_required
def complete(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()
    goal.status = 'completed'
    db.session.commit()

    from app.services import check_achievements_on_goal_complete
    check_achievements_on_goal_complete(current_user.id)

    flash('Цель выполнена! Поздравляем!', 'success')
    return redirect(url_for('goals.index'))
