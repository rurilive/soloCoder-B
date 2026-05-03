from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Event, Meeting, MeetingParticipant
from app.schemas import (
    UserCreate, UserResponse,
    EventCreate, EventResponse,
    MeetingCreate, MeetingResponse,
)

router = APIRouter()


@router.post("/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where((User.username == user.username) | (User.email == user.email))
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已存在"
        )
    
    new_user = User(username=user.username, email=user.email)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.get("/users/", response_model=List[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/events/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(event: EventCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == event.owner_id))
    owner = result.scalar_one_or_none()
    if not owner:
        raise HTTPException(status_code=400, detail="用户不存在")
    
    new_event = Event(
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        is_public=event.is_public,
        owner_id=event.owner_id,
    )
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)
    
    result = await db.execute(
        select(Event).options(selectinload(Event.owner)).where(Event.id == new_event.id)
    )
    return result.scalar_one()


@router.get("/events/", response_model=List[EventResponse])
async def get_events(
    user_id: Optional[int] = None,
    is_public: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Event).options(selectinload(Event.owner))
    
    if user_id is not None:
        query = query.where(Event.owner_id == user_id)
    if is_public is not None:
        query = query.where(Event.is_public == is_public)
    
    result = await db.execute(query)
    events = result.scalars().all()
    return events


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Event).options(selectinload(Event.owner)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    return event


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    for key, value in event_data.model_dump().items():
        setattr(event, key, value)
    
    await db.commit()
    
    result = await db.execute(
        select(Event).options(selectinload(Event.owner)).where(Event.id == event_id)
    )
    return result.scalar_one()


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    await db.delete(event)
    await db.commit()


@router.post("/meetings/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(meeting: MeetingCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == meeting.organizer_id))
    organizer = result.scalar_one_or_none()
    if not organizer:
        raise HTTPException(status_code=400, detail="组织者不存在")
    
    new_meeting = Meeting(
        title=meeting.title,
        description=meeting.description,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        organizer_id=meeting.organizer_id,
        location=meeting.location,
    )
    db.add(new_meeting)
    await db.commit()
    await db.refresh(new_meeting)
    
    if meeting.participant_ids:
        for participant_id in meeting.participant_ids:
            result = await db.execute(select(User).where(User.id == participant_id))
            user = result.scalar_one_or_none()
            if user:
                participant = MeetingParticipant(
                    meeting_id=new_meeting.id,
                    user_id=participant_id,
                )
                db.add(participant)
        await db.commit()
    
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.organizer), selectinload(Meeting.participants).selectinload(MeetingParticipant.user))
        .where(Meeting.id == new_meeting.id)
    )
    return result.scalar_one()


@router.get("/meetings/", response_model=List[MeetingResponse])
async def get_meetings(
    organizer_id: Optional[int] = None,
    participant_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Meeting).options(
        selectinload(Meeting.organizer),
        selectinload(Meeting.participants).selectinload(MeetingParticipant.user)
    )
    
    if organizer_id is not None:
        query = query.where(Meeting.organizer_id == organizer_id)
    
    if participant_id is not None:
        query = query.join(MeetingParticipant).where(MeetingParticipant.user_id == participant_id)
    
    result = await db.execute(query)
    meetings = result.scalars().all()
    return meetings


@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(meeting_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.organizer), selectinload(Meeting.participants).selectinload(MeetingParticipant.user))
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    return meeting


@router.put("/meetings/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int,
    meeting_data: MeetingCreate,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    update_data = meeting_data.model_dump(exclude={"organizer_id", "participant_ids"})
    for key, value in update_data.items():
        setattr(meeting, key, value)
    
    await db.commit()
    
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.organizer), selectinload(Meeting.participants).selectinload(MeetingParticipant.user))
        .where(Meeting.id == meeting_id)
    )
    return result.scalar_one()


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(meeting_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    await db.delete(meeting)
    await db.commit()


@router.post("/meetings/{meeting_id}/participants/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_participant(
    meeting_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    result = await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="用户已参加该会议")
    
    participant = MeetingParticipant(meeting_id=meeting_id, user_id=user_id)
    db.add(participant)
    await db.commit()
    
    return {"message": "参与者添加成功"}


@router.put("/meetings/{meeting_id}/participants/{user_id}/status")
async def update_participant_status(
    meeting_id: int,
    user_id: int,
    status: str,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="参与者不存在")
    
    if status not in ["pending", "accepted", "declined"]:
        raise HTTPException(status_code=400, detail="无效的状态值")
    
    participant.status = status
    await db.commit()
    
    return {"message": "状态更新成功", "status": status}
