import sys
sys.path.insert(0, '/data/projects/work/soloCoder/soloCoder-B/backend')

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
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

db_session = None

@asynccontextmanager
async def override_get_db():
    global db_session
    if db_session is None:
        db_session = SessionLocal()
    yield db_session

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app, raise_server_exceptions=False)

print("\n=== Testing user registration ===")
user_data = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "TestPassword123"
}

response = client.post("/api/users/", json=user_data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 500:
    print("\n=== Getting more details with raise_server_exceptions=True ===")
    client2 = TestClient(app, raise_server_exceptions=True)
    try:
        response2 = client2.post("/api/users/", json=user_data)
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n=== Cleaning up ===")
if os.path.exists(db_path):
    os.unlink(db_path)
    print(f"Removed temp database: {db_path}")
