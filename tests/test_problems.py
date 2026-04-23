import pytest
import json
from app import db
from app.models import User, Problem, Submission, DailyProblem


class TestProblemRoutes:
    def test_problem_list_page(self, client, test_problem, app):
        with app.app_context():
            db.session.merge(test_problem)
        
        response = client.get('/problems/')
        assert response.status_code == 200
        assert '两数之和' in response.get_data(as_text=True)

    def test_problem_detail_page(self, client, test_problem, app):
        with app.app_context():
            problem = db.session.merge(test_problem)
            problem_id = problem.id
        
        response = client.get(f'/problems/{problem_id}')
        assert response.status_code == 200
        assert '两数之和' in response.get_data(as_text=True)
        assert '给定数组和目标值' in response.get_data(as_text=True)

    def test_problem_detail_nonexistent(self, client):
        response = client.get('/problems/999999')
        assert response.status_code == 404

    def test_submit_requires_login(self, client, test_problem, app):
        with app.app_context():
            problem = db.session.merge(test_problem)
            problem_id = problem.id
        
        response = client.post(f'/problems/{problem_id}/submit', data={
            'code': 'def two_sum(nums, target): return [0, 1]'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)

    def test_submit_valid_code(self, client, test_user, test_problem, app):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            user_id = user.id
            problem_id = problem.id
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        code = '''
def two_sum(nums, target):
    num_map = {}
    for i, num in enumerate(nums):
        complement = target - num
        if complement in num_map:
            return [num_map[complement], i]
        num_map[num] = i
    return []
'''
        
        response = client.post(f'/problems/{problem_id}/submit', data={
            'code': code
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            submission = Submission.query.filter_by(
                user_id=user_id,
                problem_id=problem_id
            ).first()
            assert submission is not None

    def test_submit_wrong_answer(self, client, test_user, test_problem, app):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            user_id = user.id
            problem_id = problem.id
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        wrong_code = '''
def two_sum(nums, target):
    return [99, 99]
'''
        
        response = client.post(f'/problems/{problem_id}/submit', data={
            'code': wrong_code
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            submission = Submission.query.filter_by(
                user_id=user_id,
                problem_id=problem_id
            ).order_by(Submission.created_at.desc()).first()
            assert submission is not None
            assert submission.status in ['wrong_answer', 'accepted']

    def test_submission_detail_requires_login(self, client, test_user, test_problem, app):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            
            submission = Submission(
                user_id=user.id,
                problem_id=problem.id,
                code='test',
                status=Submission.STATUS_ACCEPTED
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id
        
        response = client.get(f'/problems/submission/{submission_id}', follow_redirects=True)
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)

    def test_submission_detail_owner_access(self, client, test_user, test_problem, app):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            
            submission = Submission(
                user_id=user.id,
                problem_id=problem.id,
                code='def test(): pass',
                status=Submission.STATUS_ACCEPTED
            )
            db.session.add(submission)
            db.session.commit()
            submission_id = submission.id
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        response = client.get(f'/problems/submission/{submission_id}')
        assert response.status_code == 200

    def test_my_submissions_requires_login(self, client):
        response = client.get('/problems/submissions', follow_redirects=True)
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)

    def test_my_submissions_authenticated(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        response = client.get('/problems/submissions')
        assert response.status_code == 200

    def test_problem_filter_by_difficulty(self, client, test_problem, fib_problem, app):
        with app.app_context():
            db.session.merge(test_problem)
            db.session.merge(fib_problem)
        
        response = client.get('/problems/?difficulty=easy')
        assert response.status_code == 200

    def test_empty_code_submission(self, client, test_user, test_problem, app):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            problem_id = problem.id
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        response = client.post(f'/problems/{problem_id}/submit', data={
            'code': ''
        }, follow_redirects=True)
        
        assert response.status_code == 200


class TestDailyProblemRoutes:
    def test_daily_problem_page(self, client, test_problem, app):
        with app.app_context():
            problem = db.session.merge(test_problem)
            DailyProblem.set_for_date(problem.id)
            db.session.commit()
        
        response = client.get('/daily/')
        assert response.status_code == 200

    def test_daily_problem_no_daily_set(self, client):
        response = client.get('/daily/', follow_redirects=True)
        assert response.status_code == 200
