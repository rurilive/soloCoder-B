import pytest
from datetime import datetime, timedelta


class TestMeetingCreation:
    def test_create_meeting_success(self, client, test_user):
        meeting_data = {
            "title": "测试会议",
            "description": "这是一个测试会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "location": "会议室A",
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 201
        meeting = response.json()
        assert meeting["title"] == meeting_data["title"]
        assert meeting["organizer_id"] == test_user["id"]
        assert "id" in meeting
        assert "participants" in meeting
    
    def test_create_meeting_with_participants(self, client, test_user, test_user2):
        meeting_data = {
            "title": "带参与者的会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "location": "线上会议",
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 201
        meeting = response.json()
        assert len(meeting["participants"]) == 1
        assert meeting["participants"][0]["user_id"] == test_user2["id"]
    
    def test_create_meeting_as_other_user(self, client, test_user, test_user2):
        meeting_data = {
            "title": "尝试以他人身份创建会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user2["id"],
            "participant_ids": []
        }
        
        response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能以自己的身份组织会议" in response.json()["detail"]


class TestMeetingRetrieval:
    def test_get_meetings_as_organizer(self, client, test_user):
        meeting_data = {
            "title": "我组织的会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        response = client.get(
            f"/api/meetings/?organizer_id={test_user['id']}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        meetings = response.json()
        assert isinstance(meetings, list)
        assert len(meetings) >= 1
    
    def test_get_meetings_as_participant(self, client, test_user, test_user2):
        meeting_data = {
            "title": "我参与的会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        response = client.get(
            f"/api/meetings/?participant_id={test_user2['id']}",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 200
        meetings = response.json()
        assert any(m["title"] == "我参与的会议" for m in meetings)
    
    def test_get_meeting_details(self, client, test_user, test_user2):
        meeting_data = {
            "title": "详细会议",
            "description": "会议描述",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "location": "线上",
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.get(
            f"/api/meetings/{meeting_id}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        meeting = response.json()
        assert meeting["title"] == "详细会议"
        assert meeting["description"] == "会议描述"
        assert meeting["location"] == "线上"
        assert "organizer" in meeting
        assert "participants" in meeting
    
    def test_get_meeting_without_permission(self, client, test_user, test_user2):
        meeting_data = {
            "title": "私密会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.get(
            f"/api/meetings/{meeting_id}",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 403
        assert "无权查看此会议" in response.json()["detail"]


class TestMeetingUpdate:
    def test_update_meeting_as_organizer(self, client, test_user):
        meeting_data = {
            "title": "原始会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "location": "原地点",
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        update_data = {
            "title": "更新后的会议",
            "description": "更新后的描述",
            "start_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "location": "新地点",
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        response = client.put(
            f"/api/meetings/{meeting_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 200
        updated = response.json()
        assert updated["title"] == "更新后的会议"
        assert updated["description"] == "更新后的描述"
        assert updated["location"] == "新地点"
    
    def test_update_meeting_as_participant(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        update_data = {
            "title": "尝试修改",
            "start_time": (datetime.utcnow() + timedelta(hours=3)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        response = client.put(
            f"/api/meetings/{meeting_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能修改自己组织的会议" in response.json()["detail"]


class TestMeetingDeletion:
    def test_delete_meeting_as_organizer(self, client, test_user):
        meeting_data = {
            "title": "待删除会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        delete_response = client.delete(
            f"/api/meetings/{meeting_id}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert delete_response.status_code == 204
    
    def test_delete_meeting_as_participant(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.delete(
            f"/api/meetings/{meeting_id}",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能删除自己组织的会议" in response.json()["detail"]


class TestMeetingParticipants:
    def test_add_participant(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/meetings/{meeting_id}/participants/{test_user2['id']}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 201
        assert "参与者添加成功" in response.json()["message"]
    
    def test_add_duplicate_participant(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/meetings/{meeting_id}/participants/{test_user2['id']}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 400
        assert "用户已参加该会议" in response.json()["detail"]
    
    def test_update_participant_status(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.put(
            f"/api/meetings/{meeting_id}/participants/{test_user2['id']}/status?status=accepted",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"
    
    def test_update_other_participant_status(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.put(
            f"/api/meetings/{meeting_id}/participants/{test_user2['id']}/status?status=accepted",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 403
        assert "只能修改自己的参与状态" in response.json()["detail"]
    
    def test_update_participant_nonexistent_meeting(self, client, test_user):
        response = client.put(
            "/api/meetings/9999/participants/1/status?status=accepted",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "参与者不存在" in response.json()["detail"]
    
    def test_update_participant_invalid_status(self, client, test_user, test_user2):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": [test_user2["id"]]
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.put(
            f"/api/meetings/{meeting_id}/participants/{test_user2['id']}/status?status=invalid",
            headers={"Authorization": f"Bearer {test_user2['token']}"}
        )
        
        assert response.status_code == 400
        assert "无效的状态值" in response.json()["detail"]


class TestMeetingEdgeCases:
    def test_create_meeting_with_nonexistent_organizer(self, client, test_user):
        meeting_data = {
            "title": "测试会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": 9999,
            "participant_ids": []
        }
        
        response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 403
    
    def test_add_participant_to_nonexistent_meeting(self, client, test_user, test_user2):
        response = client.post(
            f"/api/meetings/9999/participants/{test_user2['id']}",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "会议不存在" in response.json()["detail"]
    
    def test_add_nonexistent_user_as_participant(self, client, test_user):
        meeting_data = {
            "title": "会议",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        create_response = client.post(
            "/api/meetings/",
            json=meeting_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        meeting_id = create_response.json()["id"]
        
        response = client.post(
            f"/api/meetings/{meeting_id}/participants/9999",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "用户不存在" in response.json()["detail"]
    
    def test_update_nonexistent_meeting(self, client, test_user):
        update_data = {
            "title": "尝试更新",
            "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
            "organizer_id": test_user["id"],
            "participant_ids": []
        }
        
        response = client.put(
            "/api/meetings/9999",
            json=update_data,
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "会议不存在" in response.json()["detail"]
    
    def test_delete_nonexistent_meeting(self, client, test_user):
        response = client.delete(
            "/api/meetings/9999",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "会议不存在" in response.json()["detail"]
    
    def test_get_nonexistent_meeting(self, client, test_user):
        response = client.get(
            "/api/meetings/9999",
            headers={"Authorization": f"Bearer {test_user['token']}"}
        )
        
        assert response.status_code == 404
        assert "会议不存在" in response.json()["detail"]
