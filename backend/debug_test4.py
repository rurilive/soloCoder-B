import sys
sys.path.insert(0, '/data/projects/work/soloCoder/soloCoder-B/backend')

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os

from app.database import Base, get_db
from app.main import app

db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
db_path = db_file.name
db_file.close()

TEST_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
print(f"Database URL: {TEST_DATABASE_URL}")

async_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

loop.run_until_complete(init_db())

async_session_factory = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

session_holder = {}

async def override_get_db():
    if "session" not in session_holder:
        session_holder["session"] = async_session_factory()
    yield session_holder["session"]

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app, raise_server_exceptions=False)

print("\n=== 1. Testing user registration ===")
register_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123"
}
response = client.post("/api/users/", json=register_data)
print(f"Register Status: {response.status_code}")

print("\n=== 2. Testing user login ===")
login_data = {
    "username": "testuser",
    "password": "TestPassword123"
}
response = client.post("/api/users/login", json=login_data)
print(f"Login Status: {response.status_code}")

if response.status_code == 200:
    token = response.json()
    print(f"\nToken: {token}")
    
    print("\n=== 3. Testing get users with token ===")
    users_response = client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    print(f"Get Users Status: {users_response.status_code}")
    print(f"Get Users Response: {users_response.text}")
    
    print("\n=== 4. Testing create event ===")
    from datetime import datetime, timedelta
    event_data = {
        "title": "测试日程",
        "description": "这是一个测试日程",
        "start_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "end_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "is_public": False,
        "owner_id": 1
    }
    
    event_response = client.post(
        "/api/events/",
        json=event_data,
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    print(f"Create Event Status: {event_response.status_code}")
    print(f"Create Event Response: {event_response.text}")

print("\n=== Cleaning up ===")
if "session" in session_holder:
    loop.run_until_complete(session_holder["session"].close())

loop.run_until_complete(async_engine.dispose())
loop.close()

if os.path.exists(db_path):
    os.unlink(db_path)
    print(f"Removed temp database: {db_path}")
