import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.auth import get_password_hash


@pytest.fixture(scope="function")
def test_engine(tmp_path):
    db_path = tmp_path / "test.db"
    TEST_DATABASE_URL = f"sqlite:///{db_path}"
    
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def test_session_factory(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session(test_session_factory):
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(test_engine, test_session_factory, db_session):
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine as create_async_engine_async, async_sessionmaker
    from sqlalchemy.pool import StaticPool as StaticPoolAsync
    import tempfile
    import os
    
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_path = db_file.name
    db_file.close()
    
    TEST_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
    
    async_engine = create_async_engine_async(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPoolAsync,
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
    
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    
    if "session" in session_holder:
        loop.run_until_complete(session_holder["session"].close())
    
    loop.run_until_complete(async_engine.dispose())
    loop.close()
    
    if os.path.exists(db_path):
        os.unlink(db_path)
    
    app.dependency_overrides.clear()


def create_test_user_in_db(session_factory, username, email, password):
    session = session_factory()
    try:
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user.id
    finally:
        session.close()


def register_user_via_api(client, username, email, password):
    register_data = {
        "username": username,
        "email": email,
        "password": password
    }
    response = client.post("/api/users/", json=register_data)
    assert response.status_code == 201, f"注册失败: {response.text}"
    return response.json()


def login_user(client, username, password):
    login_data = {
        "username": username,
        "password": password
    }
    response = client.post("/api/users/login", json=login_data)
    assert response.status_code == 200, f"登录失败: {response.text}"
    return response.json()


def get_user_id_by_username(client, token, username):
    users_response = client.get(
        "/api/users/",
        headers={"Authorization": f"Bearer {token}"}
    )
    if users_response.status_code != 200:
        return None
    users = users_response.json()
    for u in users:
        if u["username"] == username:
            return u["id"]
    return None


@pytest.fixture(scope="function")
def test_user(client):
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123"
    }
    register_response = client.post("/api/users/", json=register_data)
    assert register_response.status_code == 201, f"注册失败: {register_response.text}"
    
    login_data = {
        "username": "testuser",
        "password": "TestPassword123"
    }
    login_response = client.post("/api/users/login", json=login_data)
    assert login_response.status_code == 200, f"登录失败: {login_response.text}"
    token = login_response.json()
    
    user_id = 1
    
    return {
        "id": user_id,
        "username": "testuser",
        "password": "TestPassword123",
        "token": token["access_token"]
    }


@pytest.fixture(scope="function")
def test_user2(client):
    register_data = {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "TestPassword123"
    }
    register_response = client.post("/api/users/", json=register_data)
    assert register_response.status_code == 201, f"注册失败: {register_response.text}"
    
    login_data = {
        "username": "testuser2",
        "password": "TestPassword123"
    }
    login_response = client.post("/api/users/login", json=login_data)
    assert login_response.status_code == 200, f"登录失败: {login_response.text}"
    token = login_response.json()
    
    user_id = 2
    
    return {
        "id": user_id,
        "username": "testuser2",
        "password": "TestPassword123",
        "token": token["access_token"]
    }
