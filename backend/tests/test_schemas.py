import pytest
from datetime import datetime

from app.schemas import (
    validate_password_complexity,
    UserCreate,
    UserLogin,
    UserBase,
    EventCreate,
    EventBase,
    MeetingCreate,
    MeetingBase,
)


class TestPasswordComplexityValidator:
    def test_validate_password_only_lowercase_fails(self):
        with pytest.raises(ValueError) as exc_info:
            validate_password_complexity("password")
        
        assert "必须包含至少两类字符" in str(exc_info.value)
    
    def test_validate_password_only_uppercase_fails(self):
        with pytest.raises(ValueError) as exc_info:
            validate_password_complexity("PASSWORD")
        
        assert "必须包含至少两类字符" in str(exc_info.value)
    
    def test_validate_password_only_digits_fails(self):
        with pytest.raises(ValueError) as exc_info:
            validate_password_complexity("12345678")
        
        assert "必须包含至少两类字符" in str(exc_info.value)
    
    def test_validate_password_only_symbols_fails(self):
        with pytest.raises(ValueError) as exc_info:
            validate_password_complexity("!@#$%^&*")
        
        assert "必须包含至少两类字符" in str(exc_info.value)
    
    def test_validate_password_lowercase_uppercase_passes(self):
        result = validate_password_complexity("Password")
        assert result == "Password"
    
    def test_validate_password_lowercase_digits_passes(self):
        result = validate_password_complexity("password123")
        assert result == "password123"
    
    def test_validate_password_uppercase_digits_passes(self):
        result = validate_password_complexity("PASSWORD123")
        assert result == "PASSWORD123"
    
    def test_validate_password_lowercase_symbol_passes(self):
        result = validate_password_complexity("password!")
        assert result == "password!"
    
    def test_validate_password_all_four_types_passes(self):
        result = validate_password_complexity("Password123!")
        assert result == "Password123!"
    
    def test_validate_password_with_edge_case_symbols(self):
        test_cases = [
            "password(", "password)", "password,", "password.",
            "password?", "password:", "password\"", "password{",
            "password}", "password|", "password<", "password>"
        ]
        for password in test_cases:
            result = validate_password_complexity(password)
            assert result == password


class TestUserBaseModel:
    def test_user_base_with_valid_email(self):
        user = UserBase(username="testuser", email="test@example.com")
        assert user.username == "testuser"
        assert user.email == "test@example.com"
    
    def test_user_base_empty_email_becomes_none(self):
        user = UserBase(username="testuser", email="")
        assert user.email is None
    
    def test_user_base_whitespace_email_becomes_none(self):
        user = UserBase(username="testuser", email="   ")
        assert user.email is None
    
    def test_user_base_none_email_stays_none(self):
        user = UserBase(username="testuser", email=None)
        assert user.email is None


class TestUserCreateModel:
    def test_user_create_valid(self):
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="StrongPass123"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.password == "StrongPass123"
    
    def test_user_create_weak_password_fails(self):
        with pytest.raises(ValueError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="weak"
            )
    
    def test_user_create_too_short_username_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                username="a",
                email="test@example.com",
                password="StrongPass123"
            )
    
    def test_user_create_too_short_password_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="a1"
            )


class TestUserLoginModel:
    def test_user_login_valid(self):
        login = UserLogin(username="testuser", password="StrongPass123")
        assert login.username == "testuser"
        assert login.password == "StrongPass123"


class TestEventBaseModel:
    def test_event_base_valid(self):
        event = EventBase(
            title="测试事件",
            description="这是一个测试",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            is_public=True
        )
        assert event.title == "测试事件"
        assert event.description == "这是一个测试"
        assert event.is_public is True
    
    def test_event_base_default_is_public_false(self):
        event = EventBase(
            title="测试事件",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        assert event.is_public is False
    
    def test_event_base_empty_title_fails(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            EventBase(
                title="",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )


class TestEventCreateModel:
    def test_event_create_valid(self):
        event = EventCreate(
            title="测试事件",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            owner_id=1
        )
        assert event.owner_id == 1


class TestMeetingBaseModel:
    def test_meeting_base_valid(self):
        meeting = MeetingBase(
            title="测试会议",
            description="会议描述",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            location="会议室A"
        )
        assert meeting.title == "测试会议"
        assert meeting.location == "会议室A"
    
    def test_meeting_base_location_optional(self):
        meeting = MeetingBase(
            title="测试会议",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        assert meeting.location is None


class TestMeetingCreateModel:
    def test_meeting_create_valid(self):
        meeting = MeetingCreate(
            title="测试会议",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            organizer_id=1,
            participant_ids=[2, 3]
        )
        assert meeting.organizer_id == 1
        assert meeting.participant_ids == [2, 3]
    
    def test_meeting_create_participant_ids_optional(self):
        meeting = MeetingCreate(
            title="测试会议",
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            organizer_id=1
        )
        assert meeting.participant_ids is None
