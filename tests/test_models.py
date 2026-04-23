import pytest
import json
from datetime import date
from app import db
from app.models import User, Problem, Submission, DailyProblem


class TestUserModel:
    def test_create_user(self, app):
        with app.app_context():
            user = User(
                username='newuser',
                email='new@example.com'
            )
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'newuser'
            assert user.email == 'new@example.com'
            assert user.is_admin is False
            assert user.check_password('testpass') is True
            assert user.check_password('wrong') is False

    def test_user_password_hash_not_stored(self, app):
        with app.app_context():
            user = User(
                username='testuser',
                email='test@example.com'
            )
            user.set_password('mypassword')
            db.session.add(user)
            db.session.commit()
            
            assert user.password_hash != 'mypassword'
            assert user.check_password('mypassword') is True

    def test_unique_username(self, app):
        with app.app_context():
            user1 = User(username='sameuser', email='user1@example.com')
            user1.set_password('pass1')
            db.session.add(user1)
            db.session.commit()
            
            user2 = User(username='sameuser', email='user2@example.com')
            user2.set_password('pass2')
            db.session.add(user2)
            
            with pytest.raises(Exception):
                db.session.commit()

    def test_unique_email(self, app):
        with app.app_context():
            user1 = User(username='user1', email='same@example.com')
            user1.set_password('pass1')
            db.session.add(user1)
            db.session.commit()
            
            user2 = User(username='user2', email='same@example.com')
            user2.set_password('pass2')
            db.session.add(user2)
            
            with pytest.raises(Exception):
                db.session.commit()


class TestProblemModel:
    def test_create_problem(self, app):
        with app.app_context():
            problem = Problem(
                title='测试题目',
                description='这是一个测试题目',
                difficulty='easy',
                function_name='test_func',
                test_cases=json.dumps([{'input': 1, 'expected': 2}])
            )
            db.session.add(problem)
            db.session.commit()
            
            assert problem.id is not None
            assert problem.title == '测试题目'
            assert problem.is_active is True

    def test_get_test_cases_list(self, app):
        with app.app_context():
            test_cases_data = [
                {'input': {'a': 1}, 'expected': 2, 'hidden': False},
                {'input': {'a': 3}, 'expected': 4, 'hidden': True},
            ]
            problem = Problem(
                title='测试',
                description='描述',
                difficulty='medium',
                function_name='test',
                test_cases=json.dumps(test_cases_data)
            )
            db.session.add(problem)
            db.session.commit()
            
            test_cases = problem.get_test_cases_list()
            assert len(test_cases) == 2
            assert test_cases[0]['input'] == {'a': 1}
            assert test_cases[1]['hidden'] is True

    def test_set_test_cases_list(self, app):
        with app.app_context():
            problem = Problem(
                title='测试',
                description='描述',
                difficulty='hard',
                function_name='test',
                test_cases='[]'
            )
            db.session.add(problem)
            db.session.commit()
            
            new_test_cases = [
                {'input': [1, 2], 'expected': 3},
                {'input': [4, 5], 'expected': 9},
            ]
            problem.set_test_cases_list(new_test_cases)
            db.session.commit()
            
            saved = problem.get_test_cases_list()
            assert len(saved) == 2
            assert saved[0]['expected'] == 3

    def test_difficulty_display(self, app):
        with app.app_context():
            p1 = Problem(title='p1', description='d1', difficulty='easy',
                        function_name='f1', test_cases='[]')
            p2 = Problem(title='p2', description='d2', difficulty='medium',
                        function_name='f2', test_cases='[]')
            p3 = Problem(title='p3', description='d3', difficulty='hard',
                        function_name='f3', test_cases='[]')
            
            assert p1.get_difficulty_display() == '简单'
            assert p2.get_difficulty_display() == '中等'
            assert p3.get_difficulty_display() == '困难'


class TestSubmissionModel:
    def test_create_submission(self, app, test_user, test_problem):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            
            submission = Submission(
                user_id=user.id,
                problem_id=problem.id,
                code='def two_sum(nums, target): return [0, 1]',
                status=Submission.STATUS_ACCEPTED
            )
            db.session.add(submission)
            db.session.commit()
            
            assert submission.id is not None
            assert submission.status == 'accepted'
            assert submission.user_id == user.id
            assert submission.problem_id == problem.id

    def test_status_display(self, app):
        submission = Submission()
        submission.status = Submission.STATUS_ACCEPTED
        assert submission.get_status_display() == '通过'
        
        submission.status = Submission.STATUS_WRONG_ANSWER
        assert submission.get_status_display() == '答案错误'
        
        submission.status = Submission.STATUS_TIME_LIMIT_EXCEEDED
        assert submission.get_status_display() == '超时'
        
        submission.status = Submission.STATUS_RUNTIME_ERROR
        assert submission.get_status_display() == '运行时错误'

    def test_test_results_serialization(self, app, test_user, test_problem):
        with app.app_context():
            user = db.session.merge(test_user)
            problem = db.session.merge(test_problem)
            
            test_results = [
                {'test_case': 1, 'passed': True, 'runtime': 1.5},
                {'test_case': 2, 'passed': False, 'error': '测试失败'},
            ]
            
            submission = Submission(
                user_id=user.id,
                problem_id=problem.id,
                code='test code',
                status=Submission.STATUS_WRONG_ANSWER
            )
            submission.set_test_results_list(test_results)
            db.session.add(submission)
            db.session.commit()
            
            saved = Submission.query.first()
            loaded = saved.get_test_results_list()
            
            assert len(loaded) == 2
            assert loaded[0]['passed'] is True
            assert loaded[1]['error'] == '测试失败'


class TestDailyProblemModel:
    def test_set_and_get_for_date(self, app, test_problem):
        with app.app_context():
            problem = db.session.merge(test_problem)
            today = date.today()
            
            DailyProblem.set_for_date(problem.id, today)
            db.session.commit()
            
            daily = DailyProblem.get_for_date(today)
            assert daily is not None
            assert daily.problem_id == problem.id
            assert daily.date == today

    def test_get_for_date_default_today(self, app, test_problem):
        with app.app_context():
            problem = db.session.merge(test_problem)
            
            DailyProblem.set_for_date(problem.id)
            db.session.commit()
            
            daily = DailyProblem.get_for_date()
            assert daily is not None
            assert daily.problem_id == problem.id

    def test_update_existing_daily_problem(self, app, test_problem, fib_problem):
        with app.app_context():
            problem1 = db.session.merge(test_problem)
            problem2 = db.session.merge(fib_problem)
            today = date.today()
            
            DailyProblem.set_for_date(problem1.id, today)
            db.session.commit()
            
            daily1 = DailyProblem.get_for_date(today)
            assert daily1.problem_id == problem1.id
            
            DailyProblem.set_for_date(problem2.id, today)
            db.session.commit()
            
            daily2 = DailyProblem.get_for_date(today)
            assert daily2.problem_id == problem2.id
            assert daily2.id == daily1.id
