import pytest
from flask import url_for
from app import db
from app.models import User


class TestAuthRoutes:
    def test_register_page_get(self, client):
        response = client.get('/auth/register')
        assert response.status_code == 200
        assert '注册' in response.get_data(as_text=True)

    def test_register_new_user(self, client, app):
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with app.app_context():
            user = User.query.filter_by(email='new@example.com').first()
            assert user is not None
            assert user.username == 'newuser'

    def test_register_duplicate_username(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'different@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        assert response.status_code == 200
        assert '用户名已被使用' in response.get_data(as_text=True)

    def test_register_duplicate_email(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        response = client.post('/auth/register', data={
            'username': 'different',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        assert response.status_code == 200
        assert '邮箱已被注册' in response.get_data(as_text=True)

    def test_register_password_mismatch(self, client):
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'confirm_password': 'different'
        })
        
        assert response.status_code == 200
        assert '密码必须一致' in response.get_data(as_text=True)

    def test_login_page_get(self, client):
        response = client.get('/auth/login')
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)

    def test_login_valid_credentials(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        assert response.status_code == 200

    def test_login_invalid_password(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        response = client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert '登录失败' in response.get_data(as_text=True)

    def test_login_nonexistent_user(self, client):
        response = client.post('/auth/login', data={
            'email': 'nonexistent@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        assert '登录失败' in response.get_data(as_text=True)

    def test_logout_authenticated_user(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_logout_anonymous_user(self, client):
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200

    def test_profile_requires_login(self, client):
        response = client.get('/auth/profile', follow_redirects=True)
        assert response.status_code == 200
        assert '登录' in response.get_data(as_text=True)

    def test_profile_authenticated_user(self, client, test_user, app):
        with app.app_context():
            db.session.merge(test_user)
        
        client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        response = client.get('/auth/profile')
        assert response.status_code == 200
        assert 'testuser' in response.get_data(as_text=True)

    def test_registered_user_can_login(self, client, app):
        client.post('/auth/register', data={
            'username': 'testreg',
            'email': 'testreg@example.com',
            'password': 'testpass',
            'confirm_password': 'testpass'
        }, follow_redirects=True)
        
        response = client.post('/auth/login', data={
            'email': 'testreg@example.com',
            'password': 'testpass'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        profile_response = client.get('/auth/profile')
        assert profile_response.status_code == 200
        assert 'testreg' in profile_response.get_data(as_text=True)
