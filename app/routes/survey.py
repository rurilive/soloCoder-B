from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.forms.survey import SurveyForm
from app.models import Survey, Question
from app.utils import login_required, survey_creator_required
from app.utils.security import log_security_event, SecurityEvent

survey = Blueprint('survey', __name__, url_prefix='/survey')

STATUS_LABELS = {
    'draft': '草稿',
    'active': '发布中',
    'paused': '暂停',
    'closed': '已结束'
}

STATUS_BADGE_CLASSES = {
    'draft': 'badge-secondary',
    'active': 'badge-success',
    'paused': 'badge-warning',
    'closed': 'badge-danger'
}

STATUS_TRANSITIONS = {
    'draft': 'active',
    'active': 'paused',
    'paused': 'active',
    'closed': 'draft'
}


@survey.route('/list')
@login_required
def list():
    status_filter = request.args.get('status', '')
    surveys_query = Survey.query.filter_by(
        creator_id=current_user.id,
        is_deleted=False
    )
    
    if status_filter:
        surveys_query = surveys_query.filter_by(status=status_filter)
    
    surveys = surveys_query.order_by(Survey.created_at.desc()).all()
    
    surveys_with_responses = []
    for s in surveys:
        surveys_with_responses.append({
            'survey': s,
            'responses_count': s.get_responses_count(),
            'status_label': STATUS_LABELS.get(s.status, s.status),
            'status_badge': STATUS_BADGE_CLASSES.get(s.status, 'badge-secondary')
        })
    
    return render_template(
        'survey/list.html',
        surveys=surveys_with_responses,
        status_filter=status_filter,
        status_labels=STATUS_LABELS
    )


@survey.route('/create', methods=['GET', 'POST'])
@survey_creator_required
def create():
    form = SurveyForm()
    if form.validate_on_submit():
        new_survey = Survey(
            title=form.title.data,
            description=form.description.data,
            status=form.status.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data,
            max_responses=form.max_responses.data,
            require_login=form.require_login.data,
            require_captcha=form.require_captcha.data,
            limit_per_ip=form.limit_per_ip.data,
            limit_per_cookie=form.limit_per_cookie.data,
            creator_id=current_user.id
        )
        
        if form.access_password.data:
            new_survey.access_password = generate_password_hash(form.access_password.data)
        
        db.session.add(new_survey)
        db.session.commit()
        
        log_security_event(
            SecurityEvent.SURVEY_CREATE,
            '问卷创建成功',
            survey_id=new_survey.id,
            survey_title=new_survey.title
        )
        
        flash('问卷创建成功！', 'success')
        return redirect(url_for('survey.list'))
    
    return render_template('survey/create.html', form=form)


@survey.route('/<int:survey_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        log_security_event(
            SecurityEvent.SUSPICIOUS_ACTIVITY,
            '用户尝试编辑无权限的问卷',
            survey_id=survey_id
        )
        flash('您没有权限编辑此问卷', 'danger')
        return redirect(url_for('survey.list'))
    
    form = SurveyForm(obj=survey_obj)
    
    if form.validate_on_submit():
        survey_obj.title = form.title.data
        survey_obj.description = form.description.data
        survey_obj.status = form.status.data
        survey_obj.start_time = form.start_time.data
        survey_obj.end_time = form.end_time.data
        survey_obj.max_responses = form.max_responses.data
        survey_obj.require_login = form.require_login.data
        survey_obj.require_captcha = form.require_captcha.data
        survey_obj.limit_per_ip = form.limit_per_ip.data
        survey_obj.limit_per_cookie = form.limit_per_cookie.data
        
        if form.access_password.data:
            survey_obj.access_password = generate_password_hash(form.access_password.data)
        
        db.session.commit()
        
        log_security_event(
            SecurityEvent.SURVEY_EDIT,
            '问卷编辑成功',
            survey_id=survey_obj.id,
            survey_title=survey_obj.title
        )
        
        flash('问卷更新成功！', 'success')
        return redirect(url_for('survey.list'))
    
    return render_template('survey/edit.html', form=form, survey=survey_obj)


@survey.route('/<int:survey_id>/status', methods=['POST'])
@login_required
def status(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        log_security_event(
            SecurityEvent.SUSPICIOUS_ACTIVITY,
            '用户尝试修改无权限问卷的状态',
            survey_id=survey_id
        )
        return jsonify({'success': False, 'message': '您没有权限操作此问卷'}), 403
    
    new_status = request.form.get('status')
    
    if not new_status:
        current_status = survey_obj.status
        new_status = STATUS_TRANSITIONS.get(current_status, current_status)
    
    if new_status in ['draft', 'active', 'paused', 'closed']:
        old_status = survey_obj.status
        survey_obj.status = new_status
        db.session.commit()
        
        log_security_event(
            SecurityEvent.SURVEY_EDIT,
            f'问卷状态变更: {old_status} -> {new_status}',
            survey_id=survey_obj.id,
            old_status=old_status,
            new_status=new_status
        )
        
        return jsonify({
            'success': True,
            'new_status': new_status,
            'status_label': STATUS_LABELS.get(new_status, new_status)
        })
    
    return jsonify({'success': False, 'message': '无效的状态'}), 400


@survey.route('/<int:survey_id>/copy', methods=['POST'])
@login_required
def copy(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        log_security_event(
            SecurityEvent.SUSPICIOUS_ACTIVITY,
            '用户尝试复制无权限的问卷',
            survey_id=survey_id
        )
        flash('您没有权限复制此问卷', 'danger')
        return redirect(url_for('survey.list'))
    
    new_survey = Survey(
        title=f"{survey_obj.title} (副本)",
        description=survey_obj.description,
        status='draft',
        start_time=None,
        end_time=None,
        access_password=None,
        max_responses=survey_obj.max_responses,
        require_login=survey_obj.require_login,
        require_captcha=survey_obj.require_captcha,
        limit_per_ip=survey_obj.limit_per_ip,
        limit_per_cookie=survey_obj.limit_per_cookie,
        creator_id=current_user.id
    )
    
    db.session.add(new_survey)
    db.session.flush()
    
    questions = Question.query.filter_by(survey_id=survey_obj.id).order_by(Question.order).all()
    for question in questions:
        new_question = Question(
            survey_id=new_survey.id,
            type=question.type,
            text=question.text,
            options=question.options,
            is_required=question.is_required,
            order=question.order,
            logic_jump=question.logic_jump
        )
        db.session.add(new_question)
    
    db.session.commit()
    
    log_security_event(
        SecurityEvent.SURVEY_CREATE,
        '问卷复制成功',
        source_survey_id=survey_obj.id,
        new_survey_id=new_survey.id
    )
    
    flash('问卷复制成功！', 'success')
    return redirect(url_for('survey.list'))


@survey.route('/<int:survey_id>/delete', methods=['POST'])
@login_required
def delete(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        log_security_event(
            SecurityEvent.SUSPICIOUS_ACTIVITY,
            '用户尝试删除无权限的问卷',
            survey_id=survey_id
        )
        return jsonify({'success': False, 'message': '您没有权限删除此问卷'}), 403
    
    survey_obj.is_deleted = True
    db.session.commit()
    
    log_security_event(
        SecurityEvent.SURVEY_DELETE,
        '问卷删除成功',
        survey_id=survey_obj.id,
        survey_title=survey_obj.title
    )
    
    return jsonify({'success': True, 'message': '问卷已删除'})
