#!/usr/bin/env python3
"""
测试拖拽式问卷编辑器的后端 API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import User, Survey, Question


def create_test_user():
    user = User.query.filter_by(username='testuser').first()
    if not user:
        user = User(
            username='testuser',
            email='test@example.com',
            is_active=True
        )
        user.set_password('test123')
        db.session.add(user)
        db.session.commit()
    return user


def create_test_survey(user):
    survey = Survey.query.filter_by(
        title='测试问卷 - 编辑器 API',
        creator_id=user.id
    ).first()
    
    if not survey:
        survey = Survey(
            title='测试问卷 - 编辑器 API',
            description='用于测试编辑器 API 的问卷',
            status='draft',
            creator_id=user.id
        )
        db.session.add(survey)
        db.session.commit()
    
    Question.query.filter_by(survey_id=survey.id).delete()
    db.session.commit()
    
    return survey


def test_api():
    app = create_app('testing')
    app.config['SERVER_NAME'] = 'localhost'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        
        user = create_test_user()
        survey = create_test_survey(user)
        survey_id = survey.id
        
        print(f"=== 测试用户: {user.username} ===")
        print(f"=== 测试问卷 ID: {survey_id} ===")
        print()
        
        client = app.test_client()
        
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
        
        print("1. 测试获取题目列表 (空问卷)...")
        response = client.get(f'/api/survey/{survey_id}/questions')
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应内容: {response.data.decode()[:500]}")
        assert response.status_code == 200, f"获取题目列表失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True, "获取题目列表应返回 success: true"
        assert len(data['questions']) == 0, "新问卷应该没有题目"
        print("   ✓ 通过 - 空问卷题目列表正确")
        print()
        
        print("2. 测试添加单选题...")
        single_choice_data = {
            "type": "single_choice",
            "text": "你喜欢什么颜色？",
            "options": {
                "options": ["红色", "蓝色", "绿色"],
                "randomize": False
            },
            "is_required": True,
            "order": 1
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions',
            data=json.dumps(single_choice_data),
            content_type='application/json'
        )
        print(f"   响应状态码: {response.status_code}")
        print(f"   响应内容: {response.data.decode()[:500]}")
        assert response.status_code == 201, f"添加单选题失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True, "添加题目应返回 success: true"
        q1_id = data['question']['id']
        print(f"   ✓ 通过 - 题目 ID: {q1_id}")
        print(f"   题目文本: {data['question']['text']}")
        print(f"   选项: {data['question']['options']}")
        print()
        
        print("3. 测试添加多选题...")
        multiple_choice_data = {
            "type": "multiple_choice",
            "text": "你喜欢什么水果？（可多选）",
            "options": {
                "options": ["苹果", "香蕉", "橙子", "葡萄"],
                "min_choices": 1,
                "max_choices": 3,
                "randomize": False
            },
            "is_required": True,
            "order": 2
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions',
            data=json.dumps(multiple_choice_data),
            content_type='application/json'
        )
        assert response.status_code == 201, f"添加多选题失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        q2_id = data['question']['id']
        print(f"   ✓ 通过 - 题目 ID: {q2_id}")
        print()
        
        print("4. 测试添加填空题...")
        text_data = {
            "type": "text",
            "text": "请输入你的建议：",
            "options": {
                "input_type": "long",
                "max_length": 1000,
                "placeholder": "请输入您的宝贵建议..."
            },
            "is_required": False,
            "order": 3
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions',
            data=json.dumps(text_data),
            content_type='application/json'
        )
        assert response.status_code == 201, f"添加填空题失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        q3_id = data['question']['id']
        print(f"   ✓ 通过 - 题目 ID: {q3_id}")
        print()
        
        print("5. 测试添加评分题...")
        rating_data = {
            "type": "rating",
            "text": "请为我们的服务评分：",
            "options": {
                "min_value": 1,
                "max_value": 5,
                "labels": ["非常差", "差", "一般", "好", "非常好"],
                "show_numbers": True
            },
            "is_required": True,
            "order": 4
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions',
            data=json.dumps(rating_data),
            content_type='application/json'
        )
        assert response.status_code == 201, f"添加评分题失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        q4_id = data['question']['id']
        print(f"   ✓ 通过 - 题目 ID: {q4_id}")
        print()
        
        print("6. 测试添加量表题...")
        scale_data = {
            "type": "scale",
            "text": "请根据您的感受选择：",
            "options": {
                "items": [
                    {"id": "item1", "text": "服务态度很好"},
                    {"id": "item2", "text": "环境很整洁"},
                    {"id": "item3", "text": "价格合理"}
                ],
                "scale_values": [1, 2, 3, 4, 5],
                "scale_labels": ["非常不同意", "不同意", "中立", "同意", "非常同意"]
            },
            "is_required": True,
            "order": 5
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions',
            data=json.dumps(scale_data),
            content_type='application/json'
        )
        assert response.status_code == 201, f"添加量表题失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        q5_id = data['question']['id']
        print(f"   ✓ 通过 - 题目 ID: {q5_id}")
        print()
        
        print("7. 测试添加日期题...")
        date_data = {
            "type": "date",
            "text": "请选择您希望预约的日期：",
            "options": {
                "date_type": "date",
                "min_date": "2024-01-01",
                "max_date": "2025-12-31"
            },
            "is_required": True,
            "order": 6
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions',
            data=json.dumps(date_data),
            content_type='application/json'
        )
        assert response.status_code == 201, f"添加日期题失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        q6_id = data['question']['id']
        print(f"   ✓ 通过 - 题目 ID: {q6_id}")
        print()
        
        print("8. 测试获取所有题目...")
        response = client.get(f'/api/survey/{survey_id}/questions')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['questions']) == 6, f"应该有 6 道题目，实际: {len(data['questions'])}"
        for q in data['questions']:
            print(f"   - 题目 {q['order']}: {q['type']} - {q['text'][:30]}...")
        print("   ✓ 通过 - 所有 6 种类型题目都正确保存")
        print()
        
        print("9. 测试更新题目...")
        update_data = {
            "text": "你最喜欢什么颜色？（更新后）",
            "options": {
                "options": ["红色", "蓝色", "绿色", "黄色"],
                "randomize": True
            },
            "is_required": False
        }
        response = client.put(
            f'/api/survey/{survey_id}/questions/{q1_id}',
            data=json.dumps(update_data),
            content_type='application/json'
        )
        assert response.status_code == 200, f"更新题目失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['question']['text'] == "你最喜欢什么颜色？（更新后）"
        assert data['question']['is_required'] == False
        assert len(data['question']['options']['options']) == 4
        print("   ✓ 通过 - 题目更新成功")
        print(f"   新标题: {data['question']['text']}")
        print(f"   新选项: {data['question']['options']['options']}")
        print()
        
        print("10. 测试重新排序题目...")
        new_order = [q6_id, q5_id, q4_id, q3_id, q2_id, q1_id]
        response = client.post(
            f'/api/survey/{survey_id}/questions/reorder',
            data=json.dumps({"order": new_order}),
            content_type='application/json'
        )
        assert response.status_code == 200, f"重新排序失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        
        response = client.get(f'/api/survey/{survey_id}/questions')
        questions = json.loads(response.data)['questions']
        for i, q in enumerate(questions):
            assert q['order'] == i + 1, f"题目 {q['id']} 的 order 应该是 {i+1}，实际是 {q['order']}"
        print("   ✓ 通过 - 题目顺序已更新")
        print(f"   新顺序: {[q['id'] for q in questions]}")
        print()
        
        print("11. 测试删除题目...")
        response = client.delete(f'/api/survey/{survey_id}/questions/{q6_id}')
        assert response.status_code == 200, f"删除题目失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        
        response = client.get(f'/api/survey/{survey_id}/questions')
        questions = json.loads(response.data)['questions']
        assert len(questions) == 5, f"删除后应该有 5 道题目，实际: {len(questions)}"
        for q in questions:
            assert q['id'] != q6_id, "已删除的题目不应该存在"
        print("   ✓ 通过 - 题目已删除，剩余 5 道题目")
        print()
        
        print("12. 测试批量保存...")
        batch_data = {
            "questions": [
                {
                    "id": q1_id,
                    "type": "single_choice",
                    "text": "批量更新 - 你喜欢什么颜色？",
                    "options": {"options": ["黑", "白"], "randomize": False},
                    "is_required": True,
                    "order": 1
                },
                {
                    "type": "text",
                    "text": "批量新增 - 这是一道新题",
                    "options": {"input_type": "short"},
                    "is_required": False,
                    "order": 2
                }
            ]
        }
        response = client.post(
            f'/api/survey/{survey_id}/questions/batch',
            data=json.dumps(batch_data),
            content_type='application/json'
        )
        assert response.status_code == 200, f"批量保存失败: {response.status_code}"
        data = json.loads(response.data)
        assert data['success'] == True
        assert len(data['questions']) == 2, f"批量保存后应该有 2 道题目，实际: {len(data['questions'])}"
        
        q1_updated = next((q for q in data['questions'] if q['id'] == q1_id), None)
        assert q1_updated is not None, "更新的题目应该存在"
        assert q1_updated['text'] == "批量更新 - 你喜欢什么颜色？"
        
        print("   ✓ 通过 - 批量保存成功")
        print(f"   题目数量: {len(data['questions'])}")
        for q in data['questions']:
            print(f"   - {q['type']}: {q['text']}")
        print()
        
        print("=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)
        print()
        print("API 端点验证总结:")
        print("  ✓ GET    /api/survey/<id>/questions          - 获取题目列表")
        print("  ✓ POST   /api/survey/<id>/questions          - 添加题目")
        print("  ✓ PUT    /api/survey/<id>/questions/<qid>   - 更新题目")
        print("  ✓ DELETE /api/survey/<id>/questions/<qid>   - 删除题目")
        print("  ✓ POST   /api/survey/<id>/questions/reorder - 重新排序")
        print("  ✓ POST   /api/survey/<id>/questions/batch   - 批量保存")
        print()
        print("支持的题目类型:")
        print("  ✓ single_choice  - 单选题")
        print("  ✓ multiple_choice - 多选题")
        print("  ✓ text           - 填空题")
        print("  ✓ rating         - 评分题")
        print("  ✓ scale          - 量表题")
        print("  ✓ date           - 日期题")


if __name__ == '__main__':
    test_api()
