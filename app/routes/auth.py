from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.extensions import db, limiter
from app.forms.auth import RegistrationForm, LoginForm
from app.models import User, Role
from app.utils.security import log_security_event, SecurityEvent

auth = Blueprint('auth', __name__, url_prefix='/auth')


@auth.route('/register', methods=['GET', 'POST'])
@limiter.limit('10/hour')
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
        
        default_role = Role.query.filter_by(name='user').first()
        if default_role:
            user.roles.append(default_role)
        
        db.session.add(user)
        db.session.commit()
        
        log_security_event(
            SecurityEvent.REGISTRATION,
            '新用户注册成功',
            user_id=user.id,
            username=user.username
        )
        
        login_user(user, remember=False)
        flash('注册成功！欢迎加入，' + user.username, 'success')
        return redirect(url_for('main.index'))
    elif request.method == 'POST':
        log_security_event(
            SecurityEvent.REGISTRATION_FAILURE,
            '注册表单验证失败',
            username=form.username.data if form.username.data else None,
            email=form.email.data if form.email.data else None
        )
    
    return render_template('auth/register.html', title='注册', form=form)


@auth.route('/login', methods=['GET', 'POST'])
@limiter.limit('10/hour')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        username_or_email = form.username_or_email.data
        
        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            
            log_security_event(
                SecurityEvent.LOGIN_SUCCESS,
                '用户登录成功',
                user_id=user.id,
                username=user.username
            )
            
            flash('登录成功！欢迎回来，' + user.username, 'success')
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.index'))
        else:
            log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                '登录失败：用户名或密码错误',
                attempted_identifier=username_or_email
            )
            flash('用户名或密码错误', 'danger')
    
    return render_template('auth/login.html', title='登录', form=form)


@auth.route('/logout')
def logout():
    if current_user.is_authenticated:
        log_security_event(
            SecurityEvent.LOGOUT,
            '用户登出',
            user_id=current_user.id,
            username=current_user.username
        )
    logout_user()
    flash('您已成功登出', 'info')
    return redirect(url_for('main.index'))
