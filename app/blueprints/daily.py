from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import DailyProblem, Problem, Submission

daily = Blueprint('daily', __name__)


@daily.route('/')
def today():
    daily_problem = DailyProblem.get_for_date()
    
    if not daily_problem:
        active_problem = Problem.query.filter_by(is_active=True).order_by(Problem.id).first()
        if active_problem:
            DailyProblem.set_for_date(active_problem.id)
            db.session.commit()
            daily_problem = DailyProblem.get_for_date()
    
    if not daily_problem:
        flash('暂无每日一题。', 'warning')
        return redirect(url_for('main.index'))
    
    problem = daily_problem.problem
    
    if not problem or not problem.is_active:
        flash('每日一题已不可用。', 'warning')
        return redirect(url_for('main.index'))
    
    test_cases = problem.get_test_cases_list()
    sample_test_cases = [tc for tc in test_cases if not tc.get('hidden', False)]
    
    user_submission = None
    if current_user.is_authenticated:
        user_submission = Submission.query.filter_by(
            user_id=current_user.id,
            problem_id=problem.id
        ).order_by(Submission.created_at.desc()).first()
    
    return render_template('daily/detail.html',
                         daily_problem=daily_problem,
                         problem=problem,
                         sample_test_cases=sample_test_cases,
                         user_submission=user_submission,
                         today=date.today())
