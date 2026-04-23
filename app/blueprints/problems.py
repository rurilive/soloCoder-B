from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models import Problem, Submission
from app.test_runner import run_tests, get_submission_status

problems = Blueprint('problems', __name__)


@problems.route('/')
def list():
    page = request.args.get('page', 1, type=int)
    difficulty = request.args.get('difficulty', None)
    status = request.args.get('status', None)
    
    query = Problem.query.filter_by(is_active=True)
    
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    pagination = query.order_by(Problem.id).paginate(
        page=page, per_page=20, error_out=False
    )
    
    user_statuses = {}
    if current_user.is_authenticated:
        submissions = Submission.query.filter_by(
            user_id=current_user.id
        ).all()
        for sub in submissions:
            if sub.problem_id not in user_statuses:
                user_statuses[sub.problem_id] = sub.status
            elif user_statuses[sub.problem_id] != Submission.STATUS_ACCEPTED:
                user_statuses[sub.problem_id] = sub.status
    
    return render_template('problems/list.html',
                         pagination=pagination,
                         problems=pagination.items,
                         difficulty=difficulty,
                         user_statuses=user_statuses)


@problems.route('/<int:problem_id>')
def detail(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    if not problem.is_active:
        abort(404)
    
    test_cases = problem.get_test_cases_list()
    sample_test_cases = [tc for tc in test_cases if not tc.get('hidden', False)]
    
    user_submission = None
    if current_user.is_authenticated:
        user_submission = Submission.query.filter_by(
            user_id=current_user.id,
            problem_id=problem_id
        ).order_by(Submission.created_at.desc()).first()
    
    return render_template('problems/detail.html',
                         problem=problem,
                         sample_test_cases=sample_test_cases,
                         user_submission=user_submission)


@problems.route('/<int:problem_id>/submit', methods=['POST'])
@login_required
def submit(problem_id):
    problem = Problem.query.get_or_404(problem_id)
    if not problem.is_active:
        abort(404)
    
    code = request.form.get('code', '').strip()
    
    if not code:
        flash('请输入代码。', 'danger')
        return redirect(url_for('problems.detail', problem_id=problem_id))
    
    submission = Submission(
        user_id=current_user.id,
        problem_id=problem_id,
        code=code,
        status=Submission.STATUS_RUNNING
    )
    db.session.add(submission)
    db.session.commit()
    
    test_cases = problem.get_test_cases_list()
    
    from flask import current_app
    timeout = current_app.config.get('TEST_CODE_TIMEOUT', 5)
    
    test_result = run_tests(
        code=code,
        function_name=problem.function_name,
        test_cases=test_cases,
        timeout=timeout
    )
    
    submission.status = get_submission_status(test_result)
    submission.runtime = test_result.get('runtime')
    submission.set_test_results_list(test_result.get('results', []))
    submission.error_message = test_result.get('error')
    submission.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    if submission.status == Submission.STATUS_ACCEPTED:
        flash('恭喜！所有测试用例通过！', 'success')
    else:
        flash(f'提交结果: {submission.get_status_display()}', 'danger')
    
    return redirect(url_for('problems.submission_detail', submission_id=submission.id))


@problems.route('/submission/<int:submission_id>')
@login_required
def submission_detail(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    
    if submission.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    test_results = submission.get_test_results_list()
    
    return render_template('problems/submission.html',
                         submission=submission,
                         test_results=test_results,
                         problem=submission.problem)


@problems.route('/submissions')
@login_required
def my_submissions():
    page = request.args.get('page', 1, type=int)
    
    pagination = Submission.query.filter_by(
        user_id=current_user.id
    ).order_by(Submission.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('problems/submissions.html',
                         pagination=pagination,
                         submissions=pagination.items)
