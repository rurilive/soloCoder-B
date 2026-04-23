import json
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import Problem, User, DailyProblem, Submission
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from flask_wtf import FlaskForm

admin = Blueprint('admin', __name__)


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


class ProblemForm(FlaskForm):
    title = StringField('题目标题', validators=[
        DataRequired(), Length(min=1, max=200)
    ])
    description = TextAreaField('题目描述', validators=[
        DataRequired()
    ])
    difficulty = SelectField('难度', choices=[
        ('easy', '简单'),
        ('medium', '中等'),
        ('hard', '困难')
    ], validators=[DataRequired()])
    function_name = StringField('函数名', validators=[
        DataRequired(), Length(min=1, max=100)
    ])
    test_cases = TextAreaField('测试用例 (JSON格式)', validators=[
        DataRequired()
    ])
    correct_answer = TextAreaField('正确答案 (Python代码)')
    is_active = BooleanField('启用')
    submit = SubmitField('保存')

    def validate_test_cases(self, field):
        try:
            data = json.loads(field.data)
            if not isinstance(data, list):
                raise ValidationError('测试用例必须是数组格式。')
            for i, tc in enumerate(data):
                if 'input' not in tc or 'expected' not in tc:
                    raise ValidationError(f'测试用例 {i+1} 缺少 input 或 expected 字段。')
        except json.JSONDecodeError:
            raise ValidationError('测试用例必须是有效的 JSON 格式。')


class DailyProblemForm(FlaskForm):
    problem_id = SelectField('选择题目', coerce=int, validators=[DataRequired()])
    target_date = StringField('日期 (YYYY-MM-DD)', validators=[DataRequired()])
    submit = SubmitField('设置每日一题')


@admin.route('/')
@login_required
@admin_required
def index():
    stats = {
        'total_users': User.query.count(),
        'total_problems': Problem.query.count(),
        'active_problems': Problem.query.filter_by(is_active=True).count(),
        'total_submissions': Submission.query.count(),
    }
    
    recent_submissions = Submission.query.order_by(
        Submission.created_at.desc()
    ).limit(10).all()
    
    return render_template('admin/index.html',
                         stats=stats,
                         recent_submissions=recent_submissions)


@admin.route('/problems')
@login_required
@admin_required
def problems_list():
    page = request.args.get('page', 1, type=int)
    
    pagination = Problem.query.order_by(Problem.id).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/problems_list.html',
                         pagination=pagination,
                         problems=pagination.items)


@admin.route('/problems/create', methods=['GET', 'POST'])
@login_required
@admin_required
def problem_create():
    form = ProblemForm()
    form.is_active.data = True
    
    if form.validate_on_submit():
        problem = Problem(
            title=form.title.data,
            description=form.description.data,
            difficulty=form.difficulty.data,
            function_name=form.function_name.data,
            test_cases=form.test_cases.data,
            correct_answer=form.correct_answer.data or None,
            is_active=form.is_active.data
        )
        db.session.add(problem)
        db.session.commit()
        
        flash('题目创建成功！', 'success')
        return redirect(url_for('admin.problem_edit', problem_id=problem.id))
    
    return render_template('admin/problem_form.html', form=form, title='创建题目')


@admin.route('/problems/<int:problem_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def problem_edit(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    form = ProblemForm(obj=problem)
    
    if form.validate_on_submit():
        problem.title = form.title.data
        problem.description = form.description.data
        problem.difficulty = form.difficulty.data
        problem.function_name = form.function_name.data
        problem.test_cases = form.test_cases.data
        problem.correct_answer = form.correct_answer.data or None
        problem.is_active = form.is_active.data
        db.session.commit()
        
        flash('题目更新成功！', 'success')
        return redirect(url_for('admin.problem_edit', problem_id=problem.id))
    
    return render_template('admin/problem_form.html', form=form, title='编辑题目', problem=problem)


@admin.route('/problems/<int:problem_id>/delete', methods=['POST'])
@login_required
@admin_required
def problem_delete(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    db.session.delete(problem)
    db.session.commit()
    
    flash('题目已删除。', 'success')
    return redirect(url_for('admin.problems_list'))


@admin.route('/users')
@login_required
@admin_required
def users_list():
    page = request.args.get('page', 1, type=int)
    
    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users_list.html',
                         pagination=pagination,
                         users=pagination.items)


@admin.route('/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def user_toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('不能修改自己的管理员状态。', 'danger')
        return redirect(url_for('admin.users_list'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    flash(f'用户 {user.username} 的管理员状态已更新。', 'success')
    return redirect(url_for('admin.users_list'))


@admin.route('/daily', methods=['GET', 'POST'])
@login_required
@admin_required
def daily_manage():
    form = DailyProblemForm()
    
    active_problems = Problem.query.filter_by(is_active=True).order_by(Problem.id).all()
    form.problem_id.choices = [(p.id, f'{p.id}. {p.title}') for p in active_problems]
    
    form.target_date.data = date.today().strftime('%Y-%m-%d')
    
    current_daily = DailyProblem.get_for_date()
    
    if form.validate_on_submit():
        try:
            from datetime import datetime
            target_date = datetime.strptime(form.target_date.data, '%Y-%m-%d').date()
            DailyProblem.set_for_date(form.problem_id.data, target_date)
            db.session.commit()
            flash(f'已设置 {target_date} 的每日一题。', 'success')
            return redirect(url_for('admin.daily_manage'))
        except ValueError:
            flash('日期格式无效，请使用 YYYY-MM-DD 格式。', 'danger')
    
    return render_template('admin/daily_manage.html',
                         form=form,
                         current_daily=current_daily)
