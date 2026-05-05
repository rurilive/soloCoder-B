from fastapi import FastAPI, HTTPException, Request, Form, Depends, status, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path
import jinja2
import secrets
import uuid
from passlib.context import CryptContext
import base64

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
import json

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBasic(auto_error=False)

AES_KEY = b'soloCoderBookmarkSecretKey2026Ab'
assert len(AES_KEY) == 32, f"AES key must be 32 bytes (256 bits), got {len(AES_KEY)}"

sessions: Dict[str, dict] = {}

def decrypt_aes(encrypted_text: str) -> str:
    try:
        iv_hex, ciphertext_b64 = encrypted_text.split(':', 1)
        iv = bytes.fromhex(iv_hex)
        ciphertext = base64.b64decode(ciphertext_b64)
        
        cipher = AES.new(AES_KEY, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
        return decrypted.decode('utf-8')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码解密失败"
        )

def create_session(user_id: int, username: str) -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "user_id": user_id,
        "username": username,
        "created_at": datetime.utcnow()
    }
    return session_id

def get_session(session_id: Optional[str] = Cookie(None)):
    if session_id and session_id in sessions:
        return sessions[session_id]
    return None

async def get_current_user_web(request: Request, session: dict = Depends(get_session)):
    if session is None:
        return None
    db = next(get_db())
    user = get_user_by_id(db, session.get("user_id"))
    return user

class NotAuthenticatedException(Exception):
    pass

async def require_login_web(session: dict = Depends(get_session)):
    if session is None:
        raise NotAuthenticatedException()
    db = next(get_db())
    user = get_user_by_id(db, session.get("user_id"))
    if not user:
        raise NotAuthenticatedException()
    return user

async def get_current_user_api(session: dict = Depends(get_session)):
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录"
        )
    db = next(get_db())
    user = get_user_by_id(db, session.get("user_id"))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )
    return user

DB_HOST = "64.83.36.96"
DB_PORT = "53306"
DB_USER = "RfohwH0Qit7LY1tcDftF"
DB_PASSWORD = "lsTiBCoLk3cWvQKMZ4Mq"
DB_NAME = "ca"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    bookmarks = relationship("BookmarkDB", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("CategoryDB", back_populates="user", cascade="all, delete-orphan")

class CategoryDB(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    parent = relationship("CategoryDB", remote_side=[id], backref="children")
    bookmarks = relationship("BookmarkDB", back_populates="category")
    user = relationship("UserDB", back_populates="categories")

class BookmarkDB(Base):
    __tablename__ = "bookmarks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    category = relationship("CategoryDB", back_populates="bookmarks")
    user = relationship("UserDB", back_populates="bookmarks")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="网络书签管理器", description="一个简单的网络书签管理应用")

@app.exception_handler(NotAuthenticatedException)
async def not_authenticated_exception_handler(request: Request, exc: NotAuthenticatedException):
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

class BookmarkBase(BaseModel):
    title: str
    url: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    category_id: Optional[int] = None

class Bookmark(BookmarkBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None
    category_name: Optional[str] = None

class BookmarkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: Optional[int] = None

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class Category(CategoryBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None
    bookmark_count: int = 0
    children: List['Category'] = []

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None

Category.update_forward_refs()

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None

class Token(BaseModel):
    username: str
    user_id: int

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def get_user_by_username(db, username: str):
    return db.query(UserDB).filter(UserDB.username == username).first()

def get_user_by_id(db, user_id: int):
    return db.query(UserDB).filter(UserDB.id == user_id).first()

def create_user_db(username: str, password: str, email: Optional[str] = None):
    db = next(get_db())
    hashed_password = get_password_hash(password)
    new_user = UserDB(
        username=username,
        password_hash=hashed_password,
        email=email,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def db_user_to_dict(user_db: UserDB) -> dict:
    return {
        "id": user_db.id,
        "username": user_db.username,
        "email": user_db.email,
        "created_at": user_db.created_at.isoformat() if user_db.created_at else None,
        "updated_at": user_db.updated_at.isoformat() if user_db.updated_at else None
    }

def db_bookmark_to_dict(bookmark_db: BookmarkDB) -> dict:
    tags = []
    if bookmark_db.tags:
        try:
            tags = json.loads(bookmark_db.tags)
        except:
            tags = []
    
    category_name = None
    if bookmark_db.category:
        category_name = bookmark_db.category.name
    
    return {
        "id": bookmark_db.id,
        "title": bookmark_db.title,
        "url": bookmark_db.url,
        "description": bookmark_db.description,
        "tags": tags,
        "category_id": bookmark_db.category_id,
        "category_name": category_name,
        "created_at": bookmark_db.created_at.isoformat() if bookmark_db.created_at else None,
        "updated_at": bookmark_db.updated_at.isoformat() if bookmark_db.updated_at else None
    }

def db_category_to_dict(category_db: CategoryDB, include_children: bool = True) -> dict:
    bookmark_count = len(category_db.bookmarks) if category_db.bookmarks else 0
    children = []
    if include_children and category_db.children:
        children = [db_category_to_dict(child, include_children=True) for child in category_db.children]
    
    return {
        "id": category_db.id,
        "name": category_db.name,
        "description": category_db.description,
        "parent_id": category_db.parent_id,
        "created_at": category_db.created_at.isoformat() if category_db.created_at else None,
        "updated_at": category_db.updated_at.isoformat() if category_db.updated_at else None,
        "bookmark_count": bookmark_count,
        "children": children
    }

def load_bookmarks(user_id: int, category_id: Optional[int] = None, search_term: Optional[str] = None):
    db = next(get_db())
    query = db.query(BookmarkDB).filter(BookmarkDB.user_id == user_id)
    
    if category_id is not None:
        query = query.filter(BookmarkDB.category_id == category_id)
    
    if search_term:
        search_lower = search_term.lower()
        query = query.filter(
            (BookmarkDB.title.ilike(f'%{search_term}%')) |
            (BookmarkDB.url.ilike(f'%{search_term}%')) |
            (BookmarkDB.description.ilike(f'%{search_term}%')) |
            (BookmarkDB.tags.ilike(f'%{search_term}%'))
        )
    
    bookmarks_db = query.order_by(BookmarkDB.created_at.desc()).all()
    return [db_bookmark_to_dict(b) for b in bookmarks_db]

def get_bookmark_by_id(bookmark_id: int, user_id: Optional[int] = None):
    db = next(get_db())
    query = db.query(BookmarkDB).filter(BookmarkDB.id == bookmark_id)
    if user_id is not None:
        query = query.filter(BookmarkDB.user_id == user_id)
    bookmark_db = query.first()
    if bookmark_db:
        return db_bookmark_to_dict(bookmark_db)
    return None

def create_bookmark_db(user_id: int, title: str, url: str, description: Optional[str] = None, 
                        tags: Optional[List[str]] = None, category_id: Optional[int] = None):
    db = next(get_db())
    
    if category_id is not None:
        category = db.query(CategoryDB).filter(
            CategoryDB.id == category_id,
            CategoryDB.user_id == user_id
        ).first()
        if not category:
            category_id = None
    
    tags_json = json.dumps(tags) if tags else "[]"
    new_bookmark = BookmarkDB(
        user_id=user_id,
        title=title,
        url=url,
        description=description,
        tags=tags_json,
        category_id=category_id,
        created_at=datetime.utcnow()
    )
    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)
    return db_bookmark_to_dict(new_bookmark)

def update_bookmark_db(bookmark_id: int, user_id: int, title: Optional[str] = None, url: Optional[str] = None, 
                       description: Optional[str] = None, tags: Optional[List[str]] = None,
                       category_id: Optional[int] = None):
    db = next(get_db())
    bookmark_db = db.query(BookmarkDB).filter(
        BookmarkDB.id == bookmark_id,
        BookmarkDB.user_id == user_id
    ).first()
    if not bookmark_db:
        return None
    
    if title is not None:
        bookmark_db.title = title
    if url is not None:
        bookmark_db.url = url
    if description is not None:
        bookmark_db.description = description
    if tags is not None:
        bookmark_db.tags = json.dumps(tags)
    if category_id is not None:
        category = db.query(CategoryDB).filter(
            CategoryDB.id == category_id,
            CategoryDB.user_id == user_id
        ).first()
        if category:
            bookmark_db.category_id = category_id
    
    bookmark_db.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bookmark_db)
    return db_bookmark_to_dict(bookmark_db)

def delete_bookmark_db(bookmark_id: int, user_id: int) -> bool:
    db = next(get_db())
    bookmark_db = db.query(BookmarkDB).filter(
        BookmarkDB.id == bookmark_id,
        BookmarkDB.user_id == user_id
    ).first()
    if bookmark_db:
        db.delete(bookmark_db)
        db.commit()
        return True
    return False

def load_categories(user_id: int, parent_id: Optional[int] = None):
    db = next(get_db())
    query = db.query(CategoryDB).filter(
        CategoryDB.user_id == user_id,
        CategoryDB.parent_id == parent_id
    ).order_by(CategoryDB.name)
    categories_db = query.all()
    return [db_category_to_dict(c) for c in categories_db]

def get_all_categories(user_id: int):
    db = next(get_db())
    categories_db = db.query(CategoryDB).filter(
        CategoryDB.user_id == user_id
    ).order_by(CategoryDB.name).all()
    return [db_category_to_dict(c, include_children=False) for c in categories_db]

def get_category_by_id(category_id: int, user_id: Optional[int] = None):
    db = next(get_db())
    query = db.query(CategoryDB).filter(CategoryDB.id == category_id)
    if user_id is not None:
        query = query.filter(CategoryDB.user_id == user_id)
    category_db = query.first()
    if category_db:
        return db_category_to_dict(category_db)
    return None

def create_category_db(user_id: int, name: str, description: Optional[str] = None, parent_id: Optional[int] = None):
    db = next(get_db())
    
    if parent_id is not None:
        parent_category = db.query(CategoryDB).filter(
            CategoryDB.id == parent_id,
            CategoryDB.user_id == user_id
        ).first()
        if not parent_category:
            parent_id = None
    
    new_category = CategoryDB(
        user_id=user_id,
        name=name,
        description=description,
        parent_id=parent_id,
        created_at=datetime.utcnow()
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return db_category_to_dict(new_category)

def update_category_db(category_id: int, user_id: int, name: Optional[str] = None, 
                       description: Optional[str] = None, parent_id: Optional[int] = None):
    db = next(get_db())
    category_db = db.query(CategoryDB).filter(
        CategoryDB.id == category_id,
        CategoryDB.user_id == user_id
    ).first()
    if not category_db:
        return None
    
    if name is not None:
        category_db.name = name
    if description is not None:
        category_db.description = description
    if parent_id is not None:
        if parent_id == category_db.id:
            parent_id = None
        else:
            parent_category = db.query(CategoryDB).filter(
                CategoryDB.id == parent_id,
                CategoryDB.user_id == user_id
            ).first()
            if not parent_category:
                parent_id = None
        category_db.parent_id = parent_id
    
    category_db.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(category_db)
    return db_category_to_dict(category_db)

def delete_category_db(category_id: int, user_id: int) -> bool:
    db = next(get_db())
    category_db = db.query(CategoryDB).filter(
        CategoryDB.id == category_id,
        CategoryDB.user_id == user_id
    ).first()
    if category_db:
        for child in category_db.children:
            child.parent_id = category_db.parent_id
        
        for bookmark in category_db.bookmarks:
            bookmark.category_id = None
        
        db.delete(category_db)
        db.commit()
        return True
    return False

def render_template(template_name: str, **context):
    template = jinja_env.get_template(template_name)
    return template.render(**context)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    html_content = render_template("login.html", request=request, messages=[])
    return HTMLResponse(content=html_content)

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    html_content = render_template("register.html", request=request, messages=[])
    return HTMLResponse(content=html_content)

@app.post("/api/users/register", response_model=User)
def register(user_data: UserCreate):
    db = next(get_db())
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    password = decrypt_aes(user_data.password)
    
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少为6个字符")
    
    new_user = create_user_db(
        username=user_data.username,
        password=password,
        email=user_data.email
    )
    return db_user_to_dict(new_user)

@app.post("/api/users/login")
def login(credentials: UserLogin):
    db = next(get_db())
    user = get_user_by_username(db, credentials.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    password = decrypt_aes(credentials.password)
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    session_id = create_session(user.id, user.username)
    response = JSONResponse(content={"username": user.username, "user_id": user.id})
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    return response

@app.post("/api/users/logout")
def logout(session: dict = Depends(get_session)):
    if session:
        for key in list(sessions.keys()):
            if sessions[key] == session:
                del sessions[key]
                break
    response = JSONResponse(content={"message": "已登出"})
    response.delete_cookie("session_id")
    return response

@app.get("/api/users/me", response_model=User)
def get_current_user_info(current_user: UserDB = Depends(get_current_user_api)):
    return db_user_to_dict(current_user)

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request, 
    category_id: Optional[int] = None, 
    search: Optional[str] = None,
    current_user: UserDB = Depends(require_login_web)
):
    bookmarks = load_bookmarks(user_id=current_user.id, category_id=category_id, search_term=search)
    categories = load_categories(user_id=current_user.id)
    all_categories = get_all_categories(user_id=current_user.id)
    
    current_category = None
    if category_id is not None:
        current_category = get_category_by_id(category_id, user_id=current_user.id)
    
    html_content = render_template(
        "index.html", 
        request=request, 
        bookmarks=bookmarks, 
        categories=categories,
        all_categories=all_categories,
        current_category=current_category,
        search_term=search,
        messages=[],
        current_user=db_user_to_dict(current_user)
    )
    return HTMLResponse(content=html_content)

@app.get("/categories", response_class=HTMLResponse)
async def categories_list(
    request: Request,
    current_user: UserDB = Depends(require_login_web)
):
    categories = load_categories(user_id=current_user.id)
    all_categories = get_all_categories(user_id=current_user.id)
    html_content = render_template(
        "categories.html", 
        request=request, 
        categories=categories,
        all_categories=all_categories,
        messages=[],
        current_user=db_user_to_dict(current_user)
    )
    return HTMLResponse(content=html_content)

@app.get("/categories/add", response_class=HTMLResponse)
async def add_category_form(
    request: Request,
    current_user: UserDB = Depends(require_login_web)
):
    all_categories = get_all_categories(user_id=current_user.id)
    html_content = render_template(
        "add_category.html", 
        request=request, 
        all_categories=all_categories,
        messages=[],
        current_user=db_user_to_dict(current_user)
    )
    return HTMLResponse(content=html_content)

@app.post("/categories/add", response_class=RedirectResponse)
async def add_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    current_user: UserDB = Depends(require_login_web)
):
    create_category_db(
        user_id=current_user.id,
        name=name,
        description=description,
        parent_id=parent_id
    )
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/categories/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_form(
    request: Request, 
    category_id: int,
    current_user: UserDB = Depends(require_login_web)
):
    category = get_category_by_id(category_id, user_id=current_user.id)
    if not category:
        return RedirectResponse(url="/categories", status_code=303)
    
    all_categories = [c for c in get_all_categories(user_id=current_user.id) if c['id'] != category_id]
    html_content = render_template(
        "edit_category.html", 
        request=request, 
        category=category,
        all_categories=all_categories,
        messages=[],
        current_user=db_user_to_dict(current_user)
    )
    return HTMLResponse(content=html_content)

@app.post("/categories/edit/{category_id}", response_class=RedirectResponse)
async def edit_category(
    category_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    current_user: UserDB = Depends(require_login_web)
):
    update_category_db(
        category_id=category_id,
        user_id=current_user.id,
        name=name,
        description=description,
        parent_id=parent_id
    )
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/categories/delete/{category_id}", response_class=RedirectResponse)
async def delete_category_web(
    category_id: int,
    current_user: UserDB = Depends(require_login_web)
):
    delete_category_db(category_id, user_id=current_user.id)
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/add", response_class=HTMLResponse)
async def add_bookmark_form(
    request: Request,
    current_user: UserDB = Depends(require_login_web)
):
    all_categories = get_all_categories(user_id=current_user.id)
    html_content = render_template(
        "add.html", 
        request=request, 
        all_categories=all_categories,
        messages=[],
        current_user=db_user_to_dict(current_user)
    )
    return HTMLResponse(content=html_content)

@app.post("/add", response_class=RedirectResponse)
async def add_bookmark(
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    current_user: UserDB = Depends(require_login_web)
):
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    create_bookmark_db(
        user_id=current_user.id,
        title=title,
        url=url,
        description=description,
        tags=tags_list,
        category_id=category_id
    )
    return RedirectResponse(url="/", status_code=303)

@app.get("/edit/{bookmark_id}", response_class=HTMLResponse)
async def edit_bookmark_form(
    request: Request, 
    bookmark_id: int,
    current_user: UserDB = Depends(require_login_web)
):
    bookmark = get_bookmark_by_id(bookmark_id, user_id=current_user.id)
    if not bookmark:
        return RedirectResponse(url="/", status_code=303)
    
    all_categories = get_all_categories(user_id=current_user.id)
    html_content = render_template(
        "edit.html", 
        request=request, 
        bookmark=bookmark,
        all_categories=all_categories,
        messages=[],
        current_user=db_user_to_dict(current_user)
    )
    return HTMLResponse(content=html_content)

@app.post("/edit/{bookmark_id}", response_class=RedirectResponse)
async def edit_bookmark(
    bookmark_id: int,
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    current_user: UserDB = Depends(require_login_web)
):
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    update_bookmark_db(
        bookmark_id=bookmark_id,
        user_id=current_user.id,
        title=title,
        url=url,
        description=description,
        tags=tags_list,
        category_id=category_id
    )
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{bookmark_id}", response_class=RedirectResponse)
async def delete_bookmark_web(
    bookmark_id: int,
    current_user: UserDB = Depends(require_login_web)
):
    delete_bookmark_db(bookmark_id, user_id=current_user.id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/bookmarks", response_model=List[Bookmark])
def get_bookmarks(
    category_id: Optional[int] = None, 
    search: Optional[str] = None,
    current_user: UserDB = Depends(get_current_user_api)
):
    return load_bookmarks(user_id=current_user.id, category_id=category_id, search_term=search)

@app.get("/api/bookmarks/{bookmark_id}", response_model=Bookmark)
def get_bookmark(
    bookmark_id: int,
    current_user: UserDB = Depends(get_current_user_api)
):
    bookmark = get_bookmark_by_id(bookmark_id, user_id=current_user.id)
    if bookmark:
        return bookmark
    raise HTTPException(status_code=404, detail="书签不存在")

@app.post("/api/bookmarks", response_model=Bookmark)
def create_bookmark(
    bookmark: BookmarkBase,
    current_user: UserDB = Depends(get_current_user_api)
):
    new_bookmark = create_bookmark_db(
        user_id=current_user.id,
        title=bookmark.title,
        url=bookmark.url,
        description=bookmark.description,
        tags=bookmark.tags,
        category_id=bookmark.category_id
    )
    return new_bookmark

@app.put("/api/bookmarks/{bookmark_id}", response_model=Bookmark)
def update_bookmark(
    bookmark_id: int, 
    bookmark_update: BookmarkUpdate,
    current_user: UserDB = Depends(get_current_user_api)
):
    update_data = bookmark_update.dict(exclude_unset=True)
    updated_bookmark = update_bookmark_db(
        bookmark_id=bookmark_id,
        user_id=current_user.id,
        title=update_data.get("title"),
        url=update_data.get("url"),
        description=update_data.get("description"),
        tags=update_data.get("tags"),
        category_id=update_data.get("category_id")
    )
    if updated_bookmark:
        return updated_bookmark
    raise HTTPException(status_code=404, detail="书签不存在")

@app.delete("/api/bookmarks/{bookmark_id}")
def delete_bookmark(
    bookmark_id: int,
    current_user: UserDB = Depends(get_current_user_api)
):
    success = delete_bookmark_db(bookmark_id, user_id=current_user.id)
    if success:
        return {"message": "书签已删除"}
    raise HTTPException(status_code=404, detail="书签不存在")

@app.get("/api/categories", response_model=List[Category])
def get_categories(
    current_user: UserDB = Depends(get_current_user_api)
):
    return load_categories(user_id=current_user.id)

@app.get("/api/categories/all", response_model=List[Category])
def get_all_categories_api(
    current_user: UserDB = Depends(get_current_user_api)
):
    return get_all_categories(user_id=current_user.id)

@app.get("/api/categories/{category_id}", response_model=Category)
def get_category(
    category_id: int,
    current_user: UserDB = Depends(get_current_user_api)
):
    category = get_category_by_id(category_id, user_id=current_user.id)
    if category:
        return category
    raise HTTPException(status_code=404, detail="分类不存在")

@app.post("/api/categories", response_model=Category)
def create_category(
    category: CategoryBase,
    current_user: UserDB = Depends(get_current_user_api)
):
    new_category = create_category_db(
        user_id=current_user.id,
        name=category.name,
        description=category.description,
        parent_id=category.parent_id
    )
    return new_category

@app.put("/api/categories/{category_id}", response_model=Category)
def update_category(
    category_id: int, 
    category_update: CategoryUpdate,
    current_user: UserDB = Depends(get_current_user_api)
):
    update_data = category_update.dict(exclude_unset=True)
    updated_category = update_category_db(
        category_id=category_id,
        user_id=current_user.id,
        name=update_data.get("name"),
        description=update_data.get("description"),
        parent_id=update_data.get("parent_id")
    )
    if updated_category:
        return updated_category
    raise HTTPException(status_code=404, detail="分类不存在")

@app.delete("/api/categories/{category_id}")
def delete_category(
    category_id: int,
    current_user: UserDB = Depends(get_current_user_api)
):
    success = delete_category_db(category_id, user_id=current_user.id)
    if success:
        return {"message": "分类已删除"}
    raise HTTPException(status_code=404, detail="分类不存在")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2222)
