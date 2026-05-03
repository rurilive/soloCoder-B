import pytest
from datetime import datetime, timedelta


class TestEventCreation:
    def test_create_event_success(self, client, test_user):
        event_data = {
            "title": "测试日程",
            "description": "这是一个测试日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 201
        event = response.json()
        assert event["title"] == event_data["title"]
        assert event["owner_id"] == test_user["id"]
        assert "id" in event
        assert "created_at" in event
    
    def test_create_event_as_other_user(self, client, test_user, test_user2):
        event_data = {
            "title": "测试日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user2["id"]
        }
        
        response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能创建自己的日程" in response.json()["detail"]
    
    def test_create_event_unauthenticated(self, client, test_user):
        event_data = {
            "title": "测试日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        response = client.post("/api/events/", json=event_data)
        
        assert response.status_code in [401, 403]
    
    def test_create_event_with_empty_title(self, client, test_user):
        event_data = {
            "title": "",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 422


class TestEventRetrieval:
    def test_get_own_events(self, client, test_user):
        event_data = {
            "title": "我的日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        response = client.get(
            f"/api/events/?user_id={test_user['id']}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)
        assert len(events) >= 1
    
    def test_get_public_events(self, client, test_user, test_user2):
        event_data = {
            "title": "公开日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": True,
            "owner_id": test_user["id"]
        }
        
        client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        response = client.get(
            "/api/events/?is_public=true",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 200
        events = response.json()
        assert any(e["title"] == "公开日程" for e in events)
    
    def test_get_private_event_by_other_user(self, client, test_user, test_user2):
        event_data = {
            "title": "私有日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        create_response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        event_id = create_response.json()["id"]
        
        response = client.get(
            f"/api/events/{event_id}",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 403
        assert "无权查看此日程" in response.json()["detail"]
    
    def test_get_nonexistent_event(self, client, test_user):
        response = client.get(
            "/api/events/9999",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "事件不存在" in response.json()["detail"]


class TestEventUpdate:
    def test_update_own_event(self, client, test_user):
        event_data = {
            "title": "原始日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        create_response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        event_id = create_response.json()["id"]
        
        update_data = {
            "title": "更新后的日程",
            "description": "更新后的描述",
            "start_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "is_public": True,
            "owner_id": test_user["id"]
        }
        
        response = client.put(
            f"/api/events/{event_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["title"] == "更新后的日程"
        assert updated["description"] == "更新后的描述"
        assert updated["is_public"] == True
    
    def test_update_other_user_event(self, client, test_user, test_user2):
        event_data = {
            "title": "原始日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        create_response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        event_id = create_response.json()["id"]
        
        update_data = {
            "title": "尝试修改",
            "start_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        response = client.put(
            f"/api/events/{event_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能修改自己的日程" in response.json()["detail"]


class TestEventDeletion:
    def test_delete_own_event(self, client, test_user):
        event_data = {
            "title": "待删除日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        create_response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        event_id = create_response.json()["id"]
        
        delete_response = client.delete(
            f"/api/events/{event_id}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert delete_response.status_code == 204
        
        get_response = client.get(
            f"/api/events/{event_id}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        assert get_response.status_code == 404
    
    def test_delete_other_user_event(self, client, test_user, test_user2):
        event_data = {
            "title": "他人日程",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "is_public": False,
            "owner_id": test_user["id"]
        }
        
        create_response = client.post(
            "/api/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        event_id = create_response.json()["id"]
        
        response = client.delete(
            f"/api/events/{event_id}",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能删除自己的日程" in response.json()["detail"]
    
    def test_delete_nonexistent_event(self, client, test_user):
        response = client.delete(
            "/api/events/9999",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "事件不存在" in response.json()["detail"]
