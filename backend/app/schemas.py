import re
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, validator


class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: Optional[str] = Field(None, min_length=5, max_length=100)
    
    @validator('email', pre=True)
    def empty_email_to_none(cls, v):
        if v is None or v == '' or (isinstance(v, str) and v.strip() == ''):
            return None
        return v


def validate_password_complexity(password: str) -> str:
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_symbol = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    categories = sum([has_upper, has_lower, has_digit, has_symbol])
    
    if categories < 2:
        raise ValueError(
            '密码必须包含至少两类字符：大写字母、小写字母、数字、符号'
        )
    
    return password


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    
    @validator('password')
    def password_complexity(cls, v):
        return validate_password_complexity(v)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class EventBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    start_time: datetime
    end_time: datetime
    is_public: bool = False


class EventCreate(EventBase):
    owner_id: int


class EventResponse(EventBase):
    id: int
    owner_id: int
    created_at: datetime
    owner: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class MeetingParticipantBase(BaseModel):
    user_id: int
    status: str = "pending"


class MeetingParticipantResponse(MeetingParticipantBase):
    id: int
    meeting_id: int
    joined_at: datetime
    user: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class MeetingBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    start_time: datetime
    end_time: datetime
    location: Optional[str] = Field(None, max_length=200)


class MeetingCreate(MeetingBase):
    organizer_id: int
    participant_ids: Optional[List[int]] = None


class MeetingResponse(MeetingBase):
    id: int
    organizer_id: int
    created_at: datetime
    organizer: Optional[UserResponse] = None
    participants: List[MeetingParticipantResponse] = []

    class Config:
        from_attributes = True
