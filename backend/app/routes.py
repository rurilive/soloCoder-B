from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User, Event, Meeting, MeetingParticipant
from app.schemas import (
    UserCreate, UserResponse, UserLogin, Token,
    EventCreate, EventResponse,
    MeetingCreate, MeetingResponse,
)
from app.auth import (
    get_password_hash, verify_password, create_access_token, get_current_user
)

router = APIRouter()


@router.post("/users/", response_model=Token, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == user.username)
    )
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username, 
        email=user.email, 
        hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    access_token = create_access_token(data={"sub": new_user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/users/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalar_one_or_none()
    
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": db_user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/", response_model=List[UserResponse])
async def get_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/events/", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能创建自己的日程"
        )
    
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Event).options(selectinload(Event.owner))
    
    if user_id is not None:
        query = query.where(Event.owner_id == user_id)
    if is_public is not None:
        query = query.where(Event.is_public == is_public)
    
    result = await db.execute(query)
    events = result.scalars().all()
    
    filtered_events = []
    for event in events:
        if event.is_public or event.owner_id == current_user.id:
            filtered_events.append(event)
    
    return filtered_events


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Event).options(selectinload(Event.owner)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    if not event.is_public and event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此日程"
        )
    
    return event


@router.put("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: int,
    event_data: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    if event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己的日程"
        )
    
    for key, value in event_data.model_dump().items():
        setattr(event, key, value)
    
    await db.commit()
    
    result = await db.execute(
        select(Event).options(selectinload(Event.owner)).where(Event.id == event_id)
    )
    return result.scalar_one()


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="事件不存在")
    
    if event.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己的日程"
        )
    
    await db.delete(event)
    await db.commit()


@router.post("/meetings/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    meeting: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if meeting.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能以自己的身份组织会议"
        )
    
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
    current_user: User = Depends(get_current_user),
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
    
    filtered_meetings = []
    for meeting in meetings:
        is_organizer = meeting.organizer_id == current_user.id
        is_participant = any(p.user_id == current_user.id for p in meeting.participants)
        if is_organizer or is_participant:
            filtered_meetings.append(meeting)
    
    return filtered_meetings


@router.get("/meetings/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Meeting)
        .options(selectinload(Meeting.organizer), selectinload(Meeting.participants).selectinload(MeetingParticipant.user))
        .where(Meeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    is_organizer = meeting.organizer_id == current_user.id
    is_participant = any(p.user_id == current_user.id for p in meeting.participants)
    if not is_organizer and not is_participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权查看此会议"
        )
    
    return meeting


@router.put("/meetings/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: int,
    meeting_data: MeetingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己组织的会议"
        )
    
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
async def delete_meeting(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己组织的会议"
        )
    
    await db.delete(meeting)
    await db.commit()


@router.post("/meetings/{meeting_id}/participants/{user_id}", status_code=status.HTTP_201_CREATED)
async def add_participant(
    meeting_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="会议不存在")
    
    if meeting.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有会议组织者可以添加参与者"
        )
    
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能修改自己的参与状态"
        )
    
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
