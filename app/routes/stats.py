from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta

from app.extensions import db
from app.models import Survey, Question, Response, ResponseAnswer
from app.utils import login_required
from app.utils.stats import (
    group_by_time,
    calculate_statistics_for_single_choice,
    calculate_statistics_for_multiple_choice,
    calculate_statistics_for_rating,
    calculate_statistics_for_scale,
    calculate_statistics_for_text,
    calculate_statistics_for_date
)

stats = Blueprint('stats', __name__, url_prefix='/survey')


@stats.route('/<int:survey_id>/stats')
@login_required
def view_stats(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    if not survey_obj.can_edit(current_user.id):
        flash('您没有权限查看此问卷的统计数据', 'danger')
        return redirect(url_for('survey.list'))
    
    stats_data = get_survey_statistics(survey_id)
    
    if request.args.get('format') == 'json' or request.accept_mimetypes.best_match(['application/json', 'text/html']) == 'application/json':
        return jsonify(stats_data)
    
    return render_template('stats/index.html', survey=survey_obj, stats=stats_data)


def get_survey_statistics(survey_id):
    survey_obj = Survey.query.get_or_404(survey_id)
    
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    
    total_responses = Response.query.filter_by(survey_id=survey_id).count()
    valid_responses = Response.query.filter_by(survey_id=survey_id, is_valid=True).count()
    invalid_responses = total_responses - valid_responses
    
    responses_today = Response.query.filter(
        Response.survey_id == survey_id,
        Response.submitted_at >= today_start
    ).count()
    
    responses_this_week = Response.query.filter(
        Response.survey_id == survey_id,
        Response.submitted_at >= week_start
    ).count()
    
    all_valid_responses = Response.query.filter_by(
        survey_id=survey_id,
        is_valid=True
    ).all()
    
    time_distribution = group_by_time(all_valid_responses, interval='day')
    
    questions = Question.query.filter_by(survey_id=survey_id).order_by(Question.order).all()
    questions_stats = []
    
    for question in questions:
        valid_answers = ResponseAnswer.query.filter(
            ResponseAnswer.question_id == question.id,
            ResponseAnswer.response_id.in_([r.id for r in all_valid_responses])
        ).all()
        
        response_count = len(valid_answers)
        
        if question.type == 'single_choice':
            question_stats = calculate_statistics_for_single_choice(question, valid_answers)
        elif question.type == 'multiple_choice':
            question_stats = calculate_statistics_for_multiple_choice(question, valid_answers)
        elif question.type == 'rating':
            question_stats = calculate_statistics_for_rating(question, valid_answers)
        elif question.type == 'scale':
            question_stats = calculate_statistics_for_scale(question, valid_answers)
        elif question.type == 'text':
            question_stats = calculate_statistics_for_text(question, valid_answers)
        elif question.type == 'date':
            question_stats = calculate_statistics_for_date(question, valid_answers)
        else:
            question_stats = {'type': question.type}
        
        questions_stats.append({
            'question_id': question.id,
            'type': question.type,
            'text': question.text,
            'is_required': question.is_required,
            'response_count': response_count,
            'stats': question_stats
        })
    
    return {
        'survey': {
            'id': survey_obj.id,
            'title': survey_obj.title,
            'status': survey_obj.status
        },
        'basic_stats': {
            'total_responses': total_responses,
            'valid_responses': valid_responses,
            'invalid_responses': invalid_responses,
            'avg_completion_time': calculate_avg_completion_time(survey_id, all_valid_responses),
            'responses_today': responses_today,
            'responses_this_week': responses_this_week
        },
        'questions_stats': questions_stats,
        'time_distribution': time_distribution
    }


def calculate_avg_completion_time(survey_id, valid_responses):
    return None
