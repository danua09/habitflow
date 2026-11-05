from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, TextAreaField, SelectField,
                     BooleanField, DateField, SelectMultipleField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional
from wtforms.widgets import CheckboxInput, ListWidget


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password', message='Пароли не совпадают')])


class ProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('new_password')])


DAYS_CHOICES = [
    ('mon', 'Пн'), ('tue', 'Вт'), ('wed', 'Ср'),
    ('thu', 'Чт'), ('fri', 'Пт'), ('sat', 'Сб'), ('sun', 'Вс'),
]


class HabitForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=500)])
    category_id = SelectField('Категория', coerce=int, validators=[Optional()])
    frequency = SelectField('Частота', choices=[
        ('daily', 'Каждый день'),
        ('weekly', 'По дням недели'),
    ], validators=[DataRequired()])
    target_days = SelectMultipleField('Дни недели', choices=DAYS_CHOICES,
                                      widget=ListWidget(prefix_label=False),
                                      option_widget=CheckboxInput())
    color = StringField('Цвет', default='#0d6efd')


class CategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(max=50)])
    icon = StringField('Иконка', default='folder')
    color = StringField('Цвет', default='#6c757d')


class GoalForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=500)])
    deadline = DateField('Дедлайн', validators=[Optional()])
    habit_ids = SelectMultipleField('Привычки', coerce=int,
                                    widget=ListWidget(prefix_label=False),
                                    option_widget=CheckboxInput())
