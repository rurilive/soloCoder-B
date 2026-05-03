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

engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

import asyncio

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.get_event_loop().run_until_complete(init_db())

SessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

db_session = SessionLocal()

async def override_get_db():
    yield db_session

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app, raise_server_exceptions=True)

print("\n=== Testing user registration ===")
user_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123"
}

response = client.post("/api/users/", json=user_data)
print(f"Register Status: {response.status_code}")
print(f"Register Response: {response.text}")

print("\n=== Testing user login ===")
login_data = {
    "username": "testuser",
    "password": "TestPassword123"
}
response = client.post("/api/users/login", json=login_data)
print(f"Login Status: {response.status_code}")
print(f"Login Response: {response.text}")

if response.status_code == 200:
    token = response.json()
    print(f"\nToken: {token}")
    
    print("\n=== Testing get users ===")
    users_response = client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {token['access_token']}"}
    )
    print(f"Get Users Status: {users_response.status_code}")
    print(f"Get Users Response: {users_response.text}")
    print(f"Get Users Response type: {type(users_response.json())}")

print("\n=== Cleaning up ===")
asyncio.get_event_loop().run_until_complete(db_session.close())
asyncio.get_event_loop().run_until_complete(engine.dispose())
if os.path.exists(db_path):
    os.unlink(db_path)
    print(f"Removed temp database: {db_path}")
