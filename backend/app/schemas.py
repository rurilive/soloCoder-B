from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)


class UserCreate(UserBase):
    pass


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
