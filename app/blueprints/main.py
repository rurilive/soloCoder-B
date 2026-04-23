from flask import Blueprint, render_template
from flask_login import current_user
from app.models import Problem, DailyProblem, Submission

main = Blueprint('main', __name__)


@main.route('/')
def index():
    total_problems = Problem.query.filter_by(is_active=True).count()
    daily_problem = DailyProblem.get_for_date()
    
    stats = {}
    if current_user.is_authenticated:
        stats['total_submissions'] = Submission.query.filter_by(user_id=current_user.id).count()
        stats['accepted_submissions'] = Submission.query.filter_by(
            user_id=current_user.id, 
            status=Submission.STATUS_ACCEPTED
        ).count()
        if stats['total_submissions'] > 0:
            stats['acceptance_rate'] = round(
                (stats['accepted_submissions'] / stats['total_submissions']) * 100, 1
            )
        else:
            stats['acceptance_rate'] = 0
    
    return render_template('main/index.html', 
                         total_problems=total_problems,
                         daily_problem=daily_problem,
                         stats=stats)
