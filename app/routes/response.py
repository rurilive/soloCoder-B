from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session, make_response
from flask_login import current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import json
import uuid

from app.extensions import db, limiter
from app.models import Survey, Question, Response, ResponseAnswer
from app.forms.response import AccessPasswordForm, create_survey_response_form
from app.routes.captcha import verify_captcha
from app.utils.security import log_security_event, SecurityEvent

response = Blueprint('response', __name__)


def check_survey_access(survey, user, session_obj, request_obj):
    if survey.is_deleted:
        return False, '问卷不存在'
    
    if survey.status != 'active':
        return False, '问卷暂不可作答'
    
    now = datetime.utcnow()
    if survey.start_time and now < survey.start_time:
        return False, '问卷尚未开始'
    if survey.end_time and now > survey.end_time:
        return False, '问卷已结束'
    
    if survey.max_responses:
        if survey.get_responses_count() >= survey.max_responses:
            return False, '问卷已满'
    
    if survey.require_login and not user.is_authenticated:
        return False, '需要登录'
    
    if survey.access_password:
        session_key = f'survey_access_{survey.id}'
        if session_key not in session_obj:
            return False, '需要密码'
    
    return True, None


def check_cookie_limit(survey, request_obj):
    if not survey.limit_per_cookie:
        return False
    
    cookie_key = f'survey_answered_{survey.id}'
    return cookie_key in request_obj.cookies


def check_ip_limit(survey, request_obj, time_window_hours=24):
    if not survey.limit_per_ip or survey.limit_per_ip <= 0:
        return False, 0
    
    ip_address = request_obj.remote_addr
    if not ip_address:
        return False, 0
    
    time_threshold = datetime.utcnow() - timedelta(hours=time_window_hours)
    
    count = Response.query.filter_by(
        survey_id=survey.id,
        ip_address=ip_address
    ).filter(
        Response.submitted_at >= time_threshold
    ).count()
    
    if count >= survey.limit_per_ip:
        return True, count
    
    return False, count


def detect_anomaly(response_obj, answers_dict, questions):
    invalid_reasons = []
    
    start_time = session.get(f'survey_start_time_{response_obj.survey_id}')
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            elapsed_seconds = (response_obj.submitted_at - start_dt).total_seconds()
            
            if elapsed_seconds < 5:
                invalid_reasons.append(f'作答时间过短 ({int(elapsed_seconds)}秒)')
        except (ValueError, TypeError):
            pass
    
    choice_answers = []
    for question in questions:
        question_id = str(question.id)
        if question.type in ['single_choice', 'rating']:
            answer = answers_dict.get(question_id)
            if answer is not None:
                choice_answers.append(str(answer))
        elif question.type == 'multiple_choice':
            answer = answers_dict.get(question_id)
            if answer and isinstance(answer, list):
                choice_answers.append(str(sorted(answer)))
    
    if len(choice_answers) >= 3:
        first_answer = choice_answers[0]
        all_same = all(ans == first_answer for ans in choice_answers)
        if all_same:
            invalid_reasons.append('所有选择题答案相同')
    
    ip_address = response_obj.ip_address
    if ip_address:
        time_threshold = response_obj.submitted_at - timedelta(minutes=10)
        recent_responses = Response.query.filter_by(
            survey_id=response_obj.survey_id,
            ip_address=ip_address
        ).filter(
            Response.submitted_at >= time_threshold,
            Response.id != response_obj.id
        ).count()
        
        if recent_responses >= 3:
            invalid_reasons.append(f'同一IP短时间内多次答卷 ({recent_responses}次)')
    
    if invalid_reasons:
        return True, '; '.join(invalid_reasons)
    
    return False, None


def validate_answers(questions, answers):
    errors = []
    
    for question in questions:
        question_id = str(question.id)
        answer = answers.get(question_id)
        
        if question.is_required:
            if answer is None or answer == '':
                errors.append({
                    'question_id': question.id,
                    'question_text': question.text,
                    'error': '此题必填'
                })
                continue
            
            if question.type == 'multiple_choice':
                min_choices = question.options.get('min_choices', 1) if question.options else 1
                if isinstance(answer, list):
                    if len(answer) < min_choices:
                        errors.append({
                            'question_id': question.id,
                            'question_text': question.text,
                            'error': f'至少需要选择 {min_choices} 个选项'
                        })
                else:
                    errors.append({
                        'question_id': question.id,
                        'question_text': question.text,
                        'error': '请选择至少一个选项'
                    })
        
        if answer is None or answer == '':
            continue
        
        if question.type == 'single_choice':
            options = question.get_options_list()
            if answer not in options:
                errors.append({
                    'question_id': question.id,
                    'question_text': question.text,
                    'error': '无效的选项'
                })
        
        elif question.type == 'multiple_choice':
            if isinstance(answer, list):
                options = question.get_options_list()
                for opt in answer:
                    if opt not in options:
                        errors.append({
                            'question_id': question.id,
                            'question_text': question.text,
                            'error': f'无效的选项: {opt}'
                        })
        
        elif question.type == 'rating':
            try:
                value = int(answer)
                min_value = question.options.get('min_value', 1) if question.options else 1
                max_value = question.options.get('max_value', 5) if question.options else 5
                if value < min_value or value > max_value:
                    errors.append({
                        'question_id': question.id,
                        'question_text': question.text,
                        'error': f'评分必须在 {min_value} 到 {max_value} 之间'
                    })
            except (ValueError, TypeError):
                errors.append({
                    'question_id': question.id,
                    'question_text': question.text,
                    'error': '请输入有效的数字'
                })
        
        elif question.type == 'scale':
            items = question.options.get('items', []) if question.options else []
            scale_values = question.options.get('scale_values', []) if question.options else []
            
            if isinstance(answer, dict):
                for i in range(len(items)):
                    item_key = f'item_{i}'
                    item_value = answer.get(item_key)
                    
                    if not item_value:
                        if question.is_required:
                            errors.append({
                                'question_id': question.id,
                                'question_text': question.text,
                                'error': f'请回答第 {i+1} 个项目'
                            })
                    else:
                        try:
                            value = int(item_value)
                            if scale_values and value not in [int(v) for v in scale_values]:
                                errors.append({
                                    'question_id': question.id,
                                    'question_text': question.text,
                                    'error': f'第 {i+1} 个项目的答案不在有效范围内'
                                })
                        except (ValueError, TypeError):
                            errors.append({
                                'question_id': question.id,
                                'question_text': question.text,
                                'error': f'第 {i+1} 个项目的答案格式无效'
                            })
            elif question.is_required:
                errors.append({
                    'question_id': question.id,
                    'question_text': question.text,
                    'error': '请回答所有量表项目'
                })
        
        elif question.type == 'date':
            try:
                if isinstance(answer, str):
                    datetime.strptime(answer, '%Y-%m-%d')
                elif isinstance(answer, datetime):
                    pass
                else:
                    raise ValueError('无效的日期格式')
            except ValueError:
                errors.append({
                    'question_id': question.id,
                    'question_text': question.text,
                    'error': '请输入有效的日期格式 (YYYY-MM-DD)'
                })
    
    return errors


def save_progress_to_session(survey_id, answers):
    if 'survey_progress' not in session:
        session['survey_progress'] = {}
    
    survey_id_str = str(survey_id)
    if survey_id_str not in session['survey_progress']:
        session['survey_progress'][survey_id_str] = {}
    
    for key, value in answers.items():
        session['survey_progress'][survey_id_str][key] = value
    
    session.modified = True


def get_progress_from_session(survey_id):
    if 'survey_progress' not in session:
        return {}
    
    survey_id_str = str(survey_id)
    return session['survey_progress'].get(survey_id_str, {})


def clear_progress_from_session(survey_id):
    if 'survey_progress' in session:
        survey_id_str = str(survey_id)
        if survey_id_str in session['survey_progress']:
            del session['survey_progress'][survey_id_str]
            session.modified = True


@response.route('/s/<string:short_code>')
def take_survey_by_short_code(short_code):
    survey = Survey.query.filter_by(id=int(short_code), is_deleted=False).first_or_404()
    return take_survey(survey.id)


@response.route('/survey/<int:survey_id>/take')
def take_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    
    if check_cookie_limit(survey, request):
        return render_template('survey/already_answered.html', survey=survey)
    
    can_access, reason = check_survey_access(survey, current_user, session, request)
    
    if not can_access:
        if reason == '需要登录':
            flash('请先登录后再填写问卷', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        elif reason == '需要密码':
            return redirect(url_for('response.access_password', survey_id=survey.id))
        else:
            flash(reason, 'danger')
            return redirect(url_for('main.index'))
    
    ip_limited, ip_count = check_ip_limit(survey, request)
    if ip_limited:
        flash(f'您的IP已达到此问卷的作答限制 ({survey.limit_per_ip}次)', 'warning')
        return render_template('survey/already_answered.html', survey=survey)
    
    captcha_token = None
    if survey.require_captcha:
        captcha_token = str(uuid.uuid4())
        session[f'captcha_token_{survey.id}'] = captcha_token
        session.modified = True
    
    session[f'survey_start_time_{survey.id}'] = datetime.utcnow().isoformat()
    session.modified = True
    
    questions = Question.query.filter_by(survey_id=survey.id).order_by(Question.order).all()
    progress = get_progress_from_session(survey.id)
    
    return render_template('survey/take.html', survey=survey, questions=questions, progress=progress, captcha_token=captcha_token)


@response.route('/survey/<int:survey_id>/access-password', methods=['GET', 'POST'])
def access_password(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    
    if not survey.access_password:
        return redirect(url_for('response.take_survey', survey_id=survey.id))
    
    if check_cookie_limit(survey, request):
        return render_template('survey/already_answered.html', survey=survey)
    
    can_access, reason = check_survey_access(survey, current_user, session, request)
    if can_access:
        return redirect(url_for('response.take_survey', survey_id=survey.id))
    
    if reason == '需要登录':
        flash('请先登录后再填写问卷', 'warning')
        return redirect(url_for('auth.login', next=request.url))
    
    form = AccessPasswordForm()
    
    if form.validate_on_submit():
        if check_password_hash(survey.access_password, form.password.data):
            session_key = f'survey_access_{survey.id}'
            session[session_key] = True
            session.modified = True
            return redirect(url_for('response.take_survey', survey_id=survey.id))
        else:
            flash('密码错误，请重试', 'danger')
    
    return render_template('survey/access_password.html', survey=survey, form=form)


@response.route('/survey/<int:survey_id>/save-progress', methods=['POST'])
def save_progress(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    
    can_access, reason = check_survey_access(survey, current_user, session, request)
    if not can_access:
        return jsonify({'success': False, 'message': reason}), 403
    
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        answers = {}
        for key, value in data.items():
            if key.startswith('q_'):
                key_part = key[2:]
                if '.item_' in key_part:
                    question_id, item_key = key_part.split('.', 1)
                    if question_id not in answers:
                        answers[question_id] = {}
                    answers[question_id][item_key] = value
                else:
                    question_id = key_part
                    answers[question_id] = value
        
        save_progress_to_session(survey.id, answers)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@response.route('/survey/<int:survey_id>/submit', methods=['POST'])
@limiter.limit('20/hour')
def submit_survey(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    
    if check_cookie_limit(survey, request):
        flash('您已经填写过此问卷', 'warning')
        return redirect(url_for('response.thank_you', survey_id=survey.id))
    
    can_access, reason = check_survey_access(survey, current_user, session, request)
    if not can_access:
        if reason == '需要登录':
            flash('请先登录后再填写问卷', 'warning')
            return redirect(url_for('auth.login', next=url_for('response.take_survey', survey_id=survey.id)))
        elif reason == '需要密码':
            return redirect(url_for('response.access_password', survey_id=survey.id))
        else:
            flash(reason, 'danger')
            return redirect(url_for('main.index'))
    
    ip_limited, ip_count = check_ip_limit(survey, request)
    if ip_limited:
        log_security_event(
            SecurityEvent.SUSPICIOUS_ACTIVITY,
            f'IP 达到问卷提交限制: {ip_count} 次',
            survey_id=survey.id
        )
        flash(f'您的IP已达到此问卷的作答限制 ({survey.limit_per_ip}次)', 'danger')
        return redirect(url_for('response.take_survey', survey_id=survey.id))
    
    if survey.require_captcha:
        captcha_input = request.form.get('captcha', '')
        captcha_token = session.get(f'captcha_token_{survey.id}')
        
        if not captcha_token or not captcha_input:
            flash('请输入验证码', 'danger')
            return redirect(url_for('response.take_survey', survey_id=survey.id))
        
        if not verify_captcha(captcha_token, captcha_input):
            flash('验证码错误，请重试', 'danger')
            return redirect(url_for('response.take_survey', survey_id=survey.id))
    
    questions = Question.query.filter_by(survey_id=survey.id).order_by(Question.order).all()
    
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        answers = {}
        for key, value in data.items():
            if key.startswith('q_'):
                key_part = key[2:]
                if '.item_' in key_part:
                    question_id, item_key = key_part.split('.', 1)
                    if question_id not in answers:
                        answers[question_id] = {}
                    answers[question_id][item_key] = value
                else:
                    question_id = key_part
                    answers[question_id] = value
        
        for question in questions:
            question_id = str(question.id)
            if question.type == 'multiple_choice':
                field_name = f'q_{question.id}'
                if field_name in request.form:
                    answers[question_id] = request.form.getlist(field_name)
            elif question.type == 'scale':
                items = question.options.get('items', []) if question.options else []
                for i in range(len(items)):
                    field_name = f'q_{question.id}.item_{i}'
                    if field_name in request.form:
                        if question_id not in answers:
                            answers[question_id] = {}
                        answers[question_id][f'item_{i}'] = request.form[field_name]
        
        errors = validate_answers(questions, answers)
        
        if errors:
            for error in errors:
                flash(f'{error["question_text"]}: {error["error"]}', 'danger')
            
            save_progress_to_session(survey.id, answers)
            
            return redirect(url_for('response.take_survey', survey_id=survey.id))
        
        new_response = Response(
            survey_id=survey.id,
            user_id=current_user.id if current_user.is_authenticated else None,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:500] if request.user_agent else None
        )
        
        db.session.add(new_response)
        db.session.flush()
        
        answers_dict = {}
        for question in questions:
            question_id = str(question.id)
            answer_value = answers.get(question_id)
            
            if answer_value is not None and answer_value != '':
                if isinstance(answer_value, list):
                    answer_str = json.dumps(answer_value, ensure_ascii=False)
                    answers_dict[question_id] = answer_value
                elif isinstance(answer_value, (dict, object)):
                    answer_str = json.dumps(answer_value, ensure_ascii=False)
                    answers_dict[question_id] = answer_value
                else:
                    answer_str = str(answer_value)
                    answers_dict[question_id] = answer_value
                
                response_answer = ResponseAnswer(
                    response_id=new_response.id,
                    question_id=question.id,
                    value=answer_str
                )
                db.session.add(response_answer)
        
        is_anomaly, anomaly_reason = detect_anomaly(new_response, answers_dict, questions)
        if is_anomaly:
            new_response.is_valid = False
            new_response.invalid_reason = anomaly_reason
            log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                f'可疑问卷提交检测: {anomaly_reason}',
                survey_id=survey.id,
                response_id=new_response.id,
                anomaly_reason=anomaly_reason
            )
        
        db.session.commit()
        
        log_security_event(
            SecurityEvent.SURVEY_SUBMIT,
            '问卷提交成功',
            survey_id=survey.id,
            response_id=new_response.id,
            is_anomaly=is_anomaly
        )
        
        clear_progress_from_session(survey.id)
        
        if f'survey_start_time_{survey.id}' in session:
            del session[f'survey_start_time_{survey.id}']
            session.modified = True
        
        if f'captcha_token_{survey.id}' in session:
            del session[f'captcha_token_{survey.id}']
            session.modified = True
        
        response_obj = make_response(redirect(url_for('response.thank_you', survey_id=survey.id)))
        
        if survey.limit_per_cookie:
            cookie_key = f'survey_answered_{survey.id}'
            response_obj.set_cookie(cookie_key, 'true', max_age=365*24*60*60, httponly=True)
        
        if is_anomaly:
            flash(f'问卷提交成功。注意：您的答卷已被标记为可疑 ({anomaly_reason})。', 'warning')
        else:
            flash('问卷提交成功！感谢您的参与。', 'success')
        
        return response_obj
    
    except Exception as e:
        db.session.rollback()
        flash(f'提交失败：{str(e)}', 'danger')
        return redirect(url_for('response.take_survey', survey_id=survey.id))


@response.route('/survey/<int:survey_id>/thank-you')
def thank_you(survey_id):
    survey = Survey.query.get_or_404(survey_id)
    return render_template('survey/thank_you.html', survey=survey)
