from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, TextAreaField, SelectField,
                     BooleanField, DateField, SelectMultipleField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError, Regexp
from wtforms.widgets import CheckboxInput, ListWidget


def bcrypt_length(form, field):
    if len(field.data.encode('utf-8')) > 72:
        raise ValidationError('Пароль слишком длинный: максимум 72 байта в UTF-8.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Пароль', validators=[DataRequired(), bcrypt_length])


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])


class PasswordResetForm(FlaskForm):
    password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6, max=72), bcrypt_length])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])


class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6, max=72), bcrypt_length])
    confirm_password = PasswordField('Подтвердите пароль',
                                     validators=[DataRequired(), EqualTo('password', message='Пароли не совпадают')])


class ProfileForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6, max=72), bcrypt_length])
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
    color = StringField('Цвет', default='#0d6efd', validators=[DataRequired(), Regexp(r'^#[0-9a-fA-F]{6}$')])

    def validate_target_days(self, field):
        if self.frequency.data == 'weekly' and not field.data:
            raise ValidationError('Выберите хотя бы один день недели.')


class CategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(max=50)])
    icon = StringField('Иконка', default='folder', validators=[Optional(), Length(max=50)])
    color = StringField('Цвет', default='#6c757d', validators=[DataRequired(), Regexp(r'^#[0-9a-fA-F]{6}$')])


class GoalForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired(), Length(max=150)])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=500)])
    deadline = DateField('Дедлайн', validators=[Optional()])
    habit_ids = SelectMultipleField('Привычки', coerce=int,
                                    widget=ListWidget(prefix_label=False),
                                    option_widget=CheckboxInput())
