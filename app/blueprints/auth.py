from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Submission
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_wtf import FlaskForm

auth = Blueprint('auth', __name__)


class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired(), Length(min=3, max=80)
    ])
    email = StringField('邮箱', validators=[
        DataRequired(), Email(), Length(max=120)
    ])
    password = PasswordField('密码', validators=[
        DataRequired(), Length(min=6)
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(), EqualTo('password', message='密码必须一致')
    ])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('用户名已被使用，请选择其他用户名。')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('邮箱已被注册，请使用其他邮箱。')


class LoginForm(FlaskForm):
    email = StringField('邮箱', validators=[
        DataRequired(), Email()
    ])
    password = PasswordField('密码', validators=[
        DataRequired()
    ])
    remember = BooleanField('记住我')
    submit = SubmitField('登录')


@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功！现在可以登录了。', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('登录失败。请检查邮箱和密码。', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已成功退出登录。', 'info')
    return redirect(url_for('main.index'))


@auth.route('/profile')
@login_required
def profile():
    submissions = Submission.query.filter_by(
        user_id=current_user.id
    ).order_by(Submission.created_at.desc()).limit(10).all()
    
    return render_template('auth/profile.html', submissions=submissions)
