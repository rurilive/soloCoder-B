from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, PasswordField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class SurveyForm(FlaskForm):
    title = StringField('问卷标题', validators=[
        DataRequired(message='请输入问卷标题'),
        Length(min=1, max=200, message='标题长度应在 1 到 200 个字符之间')
    ])
    description = TextAreaField('问卷描述', validators=[
        Length(max=2000, message='描述长度不能超过 2000 个字符')
    ])
    status = SelectField('状态', choices=[
        ('draft', '草稿'),
        ('active', '发布中'),
        ('paused', '暂停'),
        ('closed', '已结束')
    ], default='draft')
    start_time = DateTimeField('开始时间', format='%Y-%m-%d %H:%M', validators=[
        Optional()
    ])
    end_time = DateTimeField('结束时间', format='%Y-%m-%d %H:%M', validators=[
        Optional()
    ])
    access_password = PasswordField('访问密码（可选）', validators=[
        Optional(),
        Length(min=0, max=128)
    ])
    max_responses = IntegerField('最大响应数', validators=[
        Optional(),
        NumberRange(min=1, message='最大响应数必须大于 0')
    ])
    require_login = BooleanField('需要登录才能填写', default=False)
    require_captcha = BooleanField('需要验证码', default=False)
    limit_per_ip = IntegerField('每IP限制次数', validators=[
        NumberRange(min=0, max=100, message='限制次数应在 0 到 100 之间')
    ], default=1)
    limit_per_cookie = BooleanField('Cookie限制（同一浏览器只能填写一次）', default=True)
    submit = SubmitField('保存')
