from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app.models import User
from app.utils.security import validate_password_strength, get_password_strength_message


class RegistrationForm(FlaskForm):
    username = StringField('用户名', validators=[
        DataRequired(message='请输入用户名'),
        Length(min=3, max=80, message='用户名长度应在 3 到 80 个字符之间')
    ])
    email = StringField('邮箱', validators=[
        DataRequired(message='请输入邮箱'),
        Email(message='请输入有效的邮箱地址')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码'),
    ])
    confirm_password = PasswordField('确认密码', validators=[
        DataRequired(message='请确认密码'),
        EqualTo('password', message='两次输入的密码不一致')
    ])
    submit = SubmitField('注册')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被注册')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册')

    def validate_password(self, password):
        is_valid, errors = validate_password_strength(password.data)
        if not is_valid:
            for error in errors:
                raise ValidationError(error)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.password.description = get_password_strength_message()


class LoginForm(FlaskForm):
    username_or_email = StringField('用户名/邮箱', validators=[
        DataRequired(message='请输入用户名或邮箱')
    ])
    password = PasswordField('密码', validators=[
        DataRequired(message='请输入密码')
    ])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')
