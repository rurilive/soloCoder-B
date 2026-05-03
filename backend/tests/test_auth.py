import pytest


class TestUserRegistration:
    def test_register_new_user_success(self, client):
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPass123"
        }
        
        response = client.post("/api/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_register_duplicate_username(self, client):
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPass123"
        }
        
        response1 = client.post("/api/users/", json=user_data)
        assert response1.status_code == 201
        
        user_data2 = {
            "username": "testuser",
            "email": "another@example.com",
            "password": "AnotherPass123"
        }
        response2 = client.post("/api/users/", json=user_data2)
        
        assert response2.status_code == 400
        assert "用户名已存在" in response2.json()["detail"]
    
    def test_register_weak_password(self, client):
        user_data = {
            "username": "weakuser",
            "email": "weak@example.com",
            "password": "weak"
        }
        
        response = client.post("/api/users/", json=user_data)
        
        assert response.status_code == 422
    
    def test_register_password_complexity(self, client):
        test_cases = [
            {"password": "password", "expected_status": 422, "description": "全小写"},
            {"password": "PASSWORD", "expected_status": 422, "description": "全大写"},
            {"password": "1234567", "expected_status": 422, "description": "全数字"},
            {"password": "Password", "expected_status": 201, "description": "小写+大写"},
            {"password": "password123", "expected_status": 201, "description": "小写+数字"},
            {"password": "Password123", "expected_status": 201, "description": "小写+大写+数字"},
            {"password": "Password123!", "expected_status": 201, "description": "包含符号"},
        ]
        
        for i, case in enumerate(test_cases):
            user_data = {
                "username": f"user{i}",
                "email": f"user{i}@test.com",
                "password": case["password"]
            }
            
            response = client.post("/api/users/", json=user_data)
            assert response.status_code == case["expected_status"], \
                f"Failed for: {case['description']} - password: {case['password']}"


class TestUserLogin:
    def test_login_success(self, client):
        register_data = {
            "username": "loginuser",
            "email": "login@example.com",
            "password": "LoginPass123"
        }
        client.post("/api/users/", json=register_data)
        
        login_data = {
            "username": "loginuser",
            "password": "LoginPass123"
        }
        response = client.post("/api/users/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client):
        register_data = {
            "username": "wrongpassuser",
            "email": "wrongpass@example.com",
            "password": "CorrectPass123"
        }
        client.post("/api/users/", json=register_data)
        
        login_data = {
            "username": "wrongpassuser",
            "password": "WrongPass456"
        }
        response = client.post("/api/users/login", json=login_data)
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        login_data = {
            "username": "nonexistent",
            "password": "SomePass123"
        }
        response = client.post("/api/users/login", json=login_data)
        
        assert response.status_code == 401
        assert "用户名或密码错误" in response.json()["detail"]


class TestUserEndpoints:
    def test_get_users_authenticated(self, client, test_user):
        response = client.get(
            "/api/users/",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        users = response.json()
        assert isinstance(users, list)
        assert len(users) >= 1
    
    def test_get_users_unauthenticated(self, client):
        response = client.get("/api/users/")
        
        assert response.status_code in [401, 403]
    
    def test_get_user_by_id(self, client, test_user):
        response = client.get(
            f"/api/users/{test_user['id']}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        user = response.json()
        assert user["id"] == test_user["id"]
        assert user["username"] == test_user["username"]
        assert "hashed_password" not in user
    
    def test_get_nonexistent_user(self, client, test_user):
        response = client.get(
            "/api/users/9999",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "用户不存在" in response.json()["detail"]
