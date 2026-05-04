from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import jinja2

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, declarative_base
import json

DB_HOST = "64.83.36.96"
DB_PORT = "53306"
DB_USER = "RfohwH0Qit7LY1tcDftF"
DB_PASSWORD = "lsTiBCoLk3cWvQKMZ4Mq"
DB_NAME = "ca"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BookmarkDB(Base):
    __tablename__ = "bookmarks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)

Base.metadata.create_all(bind=engine)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="网络书签管理器", description="一个简单的网络书签管理应用")

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

class BookmarkBase(BaseModel):
    title: str
    url: str
    description: Optional[str] = None
    tags: Optional[List[str]] = []

class Bookmark(BookmarkBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None

class BookmarkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def db_bookmark_to_dict(bookmark_db: BookmarkDB) -> dict:
    tags = []
    if bookmark_db.tags:
        try:
            tags = json.loads(bookmark_db.tags)
        except:
            tags = []
    
    return {
        "id": bookmark_db.id,
        "title": bookmark_db.title,
        "url": bookmark_db.url,
        "description": bookmark_db.description,
        "tags": tags,
        "created_at": bookmark_db.created_at.isoformat() if bookmark_db.created_at else None,
        "updated_at": bookmark_db.updated_at.isoformat() if bookmark_db.updated_at else None
    }

def load_bookmarks():
    db = next(get_db())
    bookmarks_db = db.query(BookmarkDB).order_by(BookmarkDB.created_at.desc()).all()
    return [db_bookmark_to_dict(b) for b in bookmarks_db]

def get_bookmark_by_id(bookmark_id: int):
    db = next(get_db())
    bookmark_db = db.query(BookmarkDB).filter(BookmarkDB.id == bookmark_id).first()
    if bookmark_db:
        return db_bookmark_to_dict(bookmark_db)
    return None

def create_bookmark_db(title: str, url: str, description: Optional[str] = None, tags: Optional[List[str]] = None):
    db = next(get_db())
    tags_json = json.dumps(tags) if tags else "[]"
    new_bookmark = BookmarkDB(
        title=title,
        url=url,
        description=description,
        tags=tags_json,
        created_at=datetime.utcnow()
    )
    db.add(new_bookmark)
    db.commit()
    db.refresh(new_bookmark)
    return db_bookmark_to_dict(new_bookmark)

def update_bookmark_db(bookmark_id: int, title: Optional[str] = None, url: Optional[str] = None, 
                       description: Optional[str] = None, tags: Optional[List[str]] = None):
    db = next(get_db())
    bookmark_db = db.query(BookmarkDB).filter(BookmarkDB.id == bookmark_id).first()
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
    
    bookmark_db.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bookmark_db)
    return db_bookmark_to_dict(bookmark_db)

def delete_bookmark_db(bookmark_id: int) -> bool:
    db = next(get_db())
    bookmark_db = db.query(BookmarkDB).filter(BookmarkDB.id == bookmark_id).first()
    if bookmark_db:
        db.delete(bookmark_db)
        db.commit()
        return True
    return False

def render_template(template_name: str, **context):
    template = jinja_env.get_template(template_name)
    return template.render(**context)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    bookmarks = load_bookmarks()
    html_content = render_template("index.html", request=request, bookmarks=bookmarks, messages=[])
    return HTMLResponse(content=html_content)

@app.get("/add", response_class=HTMLResponse)
async def add_bookmark_form(request: Request):
    html_content = render_template("add.html", request=request, messages=[])
    return HTMLResponse(content=html_content)

@app.post("/add", response_class=RedirectResponse)
async def add_bookmark(
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    create_bookmark_db(
        title=title,
        url=url,
        description=description,
        tags=tags_list
    )
    return RedirectResponse(url="/", status_code=303)

@app.get("/edit/{bookmark_id}", response_class=HTMLResponse)
async def edit_bookmark_form(request: Request, bookmark_id: int):
    bookmark = get_bookmark_by_id(bookmark_id)
    if not bookmark:
        return RedirectResponse(url="/", status_code=303)
    html_content = render_template("edit.html", request=request, bookmark=bookmark, messages=[])
    return HTMLResponse(content=html_content)

@app.post("/edit/{bookmark_id}", response_class=RedirectResponse)
async def edit_bookmark(
    bookmark_id: int,
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    update_bookmark_db(
        bookmark_id=bookmark_id,
        title=title,
        url=url,
        description=description,
        tags=tags_list
    )
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{bookmark_id}", response_class=RedirectResponse)
async def delete_bookmark_web(bookmark_id: int):
    delete_bookmark_db(bookmark_id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/bookmarks", response_model=List[Bookmark])
def get_bookmarks():
    return load_bookmarks()

@app.get("/api/bookmarks/{bookmark_id}", response_model=Bookmark)
def get_bookmark(bookmark_id: int):
    bookmark = get_bookmark_by_id(bookmark_id)
    if bookmark:
        return bookmark
    raise HTTPException(status_code=404, detail="书签不存在")

@app.post("/api/bookmarks", response_model=Bookmark)
def create_bookmark(bookmark: BookmarkBase):
    new_bookmark = create_bookmark_db(
        title=bookmark.title,
        url=bookmark.url,
        description=bookmark.description,
        tags=bookmark.tags
    )
    return new_bookmark

@app.put("/api/bookmarks/{bookmark_id}", response_model=Bookmark)
def update_bookmark(bookmark_id: int, bookmark_update: BookmarkUpdate):
    update_data = bookmark_update.dict(exclude_unset=True)
    updated_bookmark = update_bookmark_db(
        bookmark_id=bookmark_id,
        title=update_data.get("title"),
        url=update_data.get("url"),
        description=update_data.get("description"),
        tags=update_data.get("tags")
    )
    if updated_bookmark:
        return updated_bookmark
    raise HTTPException(status_code=404, detail="书签不存在")

@app.delete("/api/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int):
    success = delete_bookmark_db(bookmark_id)
    if success:
        return {"message": "书签已删除"}
    raise HTTPException(status_code=404, detail="书签不存在")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2222)
