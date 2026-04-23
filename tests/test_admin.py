import pytest
import json
from app import db
from app.models import User, Problem, DailyProblem


class TestAdminRoutes:
    def test_admin_index_requires_login(self, client):
        response = client.get('/admin/', follow_redirects=True)
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)

    def test_admin_index_requires_admin(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        response = client.get('/admin/')
        assert response.status_code == 403

    def test_admin_index_accessible_by_admin(self, client, test_admin, app):
        with app.app_context():
            db.session.merge(test_admin)
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.get('/admin/')
        assert response.status_code == 200

    def test_problem_list_accessible_by_admin(self, client, test_admin, test_problem, app):
        with app.app_context():
            db.session.merge(test_admin)
            db.session.merge(test_problem)
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.get('/admin/problems')
        assert response.status_code == 200

    def test_create_problem_form(self, client, test_admin, app):
        with app.app_context():
            db.session.merge(test_admin)
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.get('/admin/problems/create')
        assert response.status_code == 200
        assert '创建题目' in response.get_data(as_text=True)

    def test_create_problem_submit(self, client, test_admin, app):
        with app.app_context():
            db.session.merge(test_admin)
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        test_cases = json.dumps([
            {'input': {'n': 0}, 'expected': 0, 'hidden': False},
            {'input': {'n': 1}, 'expected': 1, 'hidden': False},
        ])
        
        response = client.post('/admin/problems/create', data={
            'title': '新测试题目',
            'description': '这是一个新的测试题目描述',
            'difficulty': 'easy',
            'function_name': 'test_func',
            'test_cases': test_cases,
            'is_active': 'y'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            problem = Problem.query.filter_by(title='新测试题目').first()
            assert problem is not None
            assert problem.function_name == 'test_func'

    def test_edit_problem(self, client, test_admin, test_problem, app):
        with app.app_context():
            db.session.merge(test_admin)
            problem = db.session.merge(test_problem)
            problem_id = problem.id
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.get(f'/admin/problems/{problem_id}/edit')
        assert response.status_code == 200

    def test_users_list_accessible_by_admin(self, client, test_admin, test_user, app):
        with app.app_context():
            db.session.merge(test_admin)
            db.session.merge(test_user)
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.get('/admin/users')
        assert response.status_code == 200
        assert 'testuser' in response.get_data(as_text=True)

    def test_toggle_admin_status(self, client, test_admin, test_user, app):
        with app.app_context():
            db.session.merge(test_admin)
            user = db.session.merge(test_user)
            user_id = user.id
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.post(f'/admin/users/{user_id}/toggle_admin', follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            updated_user = User.query.get(user_id)
            assert updated_user.is_admin is True

    def test_cannot_toggle_own_admin_status(self, client, test_admin, app):
        with app.app_context():
            admin = db.session.merge(test_admin)
            admin_id = admin.id
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.post(f'/admin/users/{admin_id}/toggle_admin', follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            updated_admin = User.query.get(admin_id)
            assert updated_admin.is_admin is True

    def test_daily_manage_accessible_by_admin(self, client, test_admin, app):
        with app.app_context():
            db.session.merge(test_admin)
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.get('/admin/daily')
        assert response.status_code == 200

    def test_set_daily_problem(self, client, test_admin, test_problem, app):
        with app.app_context():
            db.session.merge(test_admin)
            problem = db.session.merge(test_problem)
            problem_id = problem.id
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        from datetime import date
        today_str = date.today().strftime('%Y-%m-%d')
        
        response = client.post('/admin/daily', data={
            'problem_id': problem_id,
            'target_date': today_str
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            daily = DailyProblem.get_for_date()
            assert daily is not None
            assert daily.problem_id == problem_id

    def test_delete_problem(self, client, test_admin, test_problem, app):
        with app.app_context():
            db.session.merge(test_admin)
            problem = db.session.merge(test_problem)
            problem_id = problem.id
        
        client.post('/auth/login', data={
            'email': 'admin@example.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        response = client.post(f'/admin/problems/{problem_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        
        with app.app_context():
            deleted_problem = Problem.query.get(problem_id)
            assert deleted_problem is None
