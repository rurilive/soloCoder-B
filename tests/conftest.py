import pytest
import json
from app import create_app, db
from app.models import User, Problem, Submission, DailyProblem


@pytest.fixture
def app():
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        yield user


@pytest.fixture
def test_admin(app):
    with app.app_context():
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        yield admin


@pytest.fixture
def test_problem(app):
    with app.app_context():
        problem = Problem(
            title='两数之和',
            description='给定数组和目标值，返回两个数的索引',
            difficulty='easy',
            function_name='two_sum',
            test_cases=json.dumps([
                {'input': {'nums': [2, 7, 11, 15], 'target': 9}, 'expected': [0, 1], 'hidden': False},
                {'input': {'nums': [3, 2, 4], 'target': 6}, 'expected': [1, 2], 'hidden': True},
            ])
        )
        db.session.add(problem)
        db.session.commit()
        yield problem


@pytest.fixture
def fib_problem(app):
    with app.app_context():
        problem = Problem(
            title='斐波那契数',
            description='计算第n个斐波那契数',
            difficulty='easy',
            function_name='fib',
            test_cases=json.dumps([
                {'input': {'n': 2}, 'expected': 1, 'hidden': False},
                {'input': {'n': 10}, 'expected': 55, 'hidden': False},
            ])
        )
        db.session.add(problem)
        db.session.commit()
        yield problem


class AuthActions:
    def __init__(self, client):
        self._client = client

    def login(self, email='test@example.com', password='password123'):
        return self._client.post(
            '/auth/login',
            data={'email': email, 'password': password},
            follow_redirects=True
        )

    def logout(self):
        return self._client.get('/auth/logout', follow_redirects=True)


@pytest.fixture
def auth(client):
    return AuthActions(client)
