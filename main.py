from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import jinja2

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
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

class CategoryDB(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    parent = relationship("CategoryDB", remote_side=[id], backref="children")
    bookmarks = relationship("BookmarkDB", back_populates="category")

class BookmarkDB(Base):
    __tablename__ = "bookmarks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    
    category = relationship("CategoryDB", back_populates="bookmarks")

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

def load_bookmarks(category_id: Optional[int] = None, search_term: Optional[str] = None):
    db = next(get_db())
    query = db.query(BookmarkDB)
    
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

def get_bookmark_by_id(bookmark_id: int):
    db = next(get_db())
    bookmark_db = db.query(BookmarkDB).filter(BookmarkDB.id == bookmark_id).first()
    if bookmark_db:
        return db_bookmark_to_dict(bookmark_db)
    return None

def create_bookmark_db(title: str, url: str, description: Optional[str] = None, 
                        tags: Optional[List[str]] = None, category_id: Optional[int] = None):
    db = next(get_db())
    tags_json = json.dumps(tags) if tags else "[]"
    new_bookmark = BookmarkDB(
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

def update_bookmark_db(bookmark_id: int, title: Optional[str] = None, url: Optional[str] = None, 
                       description: Optional[str] = None, tags: Optional[List[str]] = None,
                       category_id: Optional[int] = None):
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
    if category_id is not None:
        bookmark_db.category_id = category_id
    
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

def load_categories(parent_id: Optional[int] = None):
    db = next(get_db())
    query = db.query(CategoryDB).filter(CategoryDB.parent_id == parent_id).order_by(CategoryDB.name)
    categories_db = query.all()
    return [db_category_to_dict(c) for c in categories_db]

def get_all_categories():
    db = next(get_db())
    categories_db = db.query(CategoryDB).order_by(CategoryDB.name).all()
    return [db_category_to_dict(c, include_children=False) for c in categories_db]

def get_category_by_id(category_id: int):
    db = next(get_db())
    category_db = db.query(CategoryDB).filter(CategoryDB.id == category_id).first()
    if category_db:
        return db_category_to_dict(category_db)
    return None

def create_category_db(name: str, description: Optional[str] = None, parent_id: Optional[int] = None):
    db = next(get_db())
    
    if parent_id is not None:
        parent_category = db.query(CategoryDB).filter(CategoryDB.id == parent_id).first()
        if not parent_category:
            parent_id = None
    
    new_category = CategoryDB(
        name=name,
        description=description,
        parent_id=parent_id,
        created_at=datetime.utcnow()
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return db_category_to_dict(new_category)

def update_category_db(category_id: int, name: Optional[str] = None, 
                       description: Optional[str] = None, parent_id: Optional[int] = None):
    db = next(get_db())
    category_db = db.query(CategoryDB).filter(CategoryDB.id == category_id).first()
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
            parent_category = db.query(CategoryDB).filter(CategoryDB.id == parent_id).first()
            if not parent_category:
                parent_id = None
        category_db.parent_id = parent_id
    
    category_db.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(category_db)
    return db_category_to_dict(category_db)

def delete_category_db(category_id: int) -> bool:
    db = next(get_db())
    category_db = db.query(CategoryDB).filter(CategoryDB.id == category_id).first()
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

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request, 
    category_id: Optional[int] = None, 
    search: Optional[str] = None
):
    bookmarks = load_bookmarks(category_id=category_id, search_term=search)
    categories = load_categories()
    all_categories = get_all_categories()
    
    current_category = None
    if category_id is not None:
        current_category = get_category_by_id(category_id)
    
    html_content = render_template(
        "index.html", 
        request=request, 
        bookmarks=bookmarks, 
        categories=categories,
        all_categories=all_categories,
        current_category=current_category,
        search_term=search,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.get("/categories", response_class=HTMLResponse)
async def categories_list(request: Request):
    categories = load_categories()
    all_categories = get_all_categories()
    html_content = render_template(
        "categories.html", 
        request=request, 
        categories=categories,
        all_categories=all_categories,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.get("/categories/add", response_class=HTMLResponse)
async def add_category_form(request: Request):
    all_categories = get_all_categories()
    html_content = render_template(
        "add_category.html", 
        request=request, 
        all_categories=all_categories,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.post("/categories/add", response_class=RedirectResponse)
async def add_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None)
):
    create_category_db(
        name=name,
        description=description,
        parent_id=parent_id
    )
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/categories/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_form(request: Request, category_id: int):
    category = get_category_by_id(category_id)
    if not category:
        return RedirectResponse(url="/categories", status_code=303)
    
    all_categories = [c for c in get_all_categories() if c['id'] != category_id]
    html_content = render_template(
        "edit_category.html", 
        request=request, 
        category=category,
        all_categories=all_categories,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.post("/categories/edit/{category_id}", response_class=RedirectResponse)
async def edit_category(
    category_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None)
):
    update_category_db(
        category_id=category_id,
        name=name,
        description=description,
        parent_id=parent_id
    )
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/categories/delete/{category_id}", response_class=RedirectResponse)
async def delete_category_web(category_id: int):
    delete_category_db(category_id)
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/add", response_class=HTMLResponse)
async def add_bookmark_form(request: Request):
    all_categories = get_all_categories()
    html_content = render_template(
        "add.html", 
        request=request, 
        all_categories=all_categories,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.post("/add", response_class=RedirectResponse)
async def add_bookmark(
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None)
):
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    create_bookmark_db(
        title=title,
        url=url,
        description=description,
        tags=tags_list,
        category_id=category_id
    )
    return RedirectResponse(url="/", status_code=303)

@app.get("/edit/{bookmark_id}", response_class=HTMLResponse)
async def edit_bookmark_form(request: Request, bookmark_id: int):
    bookmark = get_bookmark_by_id(bookmark_id)
    if not bookmark:
        return RedirectResponse(url="/", status_code=303)
    
    all_categories = get_all_categories()
    html_content = render_template(
        "edit.html", 
        request=request, 
        bookmark=bookmark,
        all_categories=all_categories,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.post("/edit/{bookmark_id}", response_class=RedirectResponse)
async def edit_bookmark(
    bookmark_id: int,
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None)
):
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    update_bookmark_db(
        bookmark_id=bookmark_id,
        title=title,
        url=url,
        description=description,
        tags=tags_list,
        category_id=category_id
    )
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{bookmark_id}", response_class=RedirectResponse)
async def delete_bookmark_web(bookmark_id: int):
    delete_bookmark_db(bookmark_id)
    return RedirectResponse(url="/", status_code=303)

@app.get("/api/bookmarks", response_model=List[Bookmark])
def get_bookmarks(category_id: Optional[int] = None, search: Optional[str] = None):
    return load_bookmarks(category_id=category_id, search_term=search)

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
        tags=bookmark.tags,
        category_id=bookmark.category_id
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
        tags=update_data.get("tags"),
        category_id=update_data.get("category_id")
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

@app.get("/api/categories", response_model=List[Category])
def get_categories():
    return load_categories()

@app.get("/api/categories/all", response_model=List[Category])
def get_all_categories_api():
    return get_all_categories()

@app.get("/api/categories/{category_id}", response_model=Category)
def get_category(category_id: int):
    category = get_category_by_id(category_id)
    if category:
        return category
    raise HTTPException(status_code=404, detail="分类不存在")

@app.post("/api/categories", response_model=Category)
def create_category(category: CategoryBase):
    new_category = create_category_db(
        name=category.name,
        description=category.description,
        parent_id=category.parent_id
    )
    return new_category

@app.put("/api/categories/{category_id}", response_model=Category)
def update_category(category_id: int, category_update: CategoryUpdate):
    update_data = category_update.dict(exclude_unset=True)
    updated_category = update_category_db(
        category_id=category_id,
        name=update_data.get("name"),
        description=update_data.get("description"),
        parent_id=update_data.get("parent_id")
    )
    if updated_category:
        return updated_category
    raise HTTPException(status_code=404, detail="分类不存在")

@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int):
    success = delete_category_db(category_id)
    if success:
        return {"message": "分类已删除"}
    raise HTTPException(status_code=404, detail="分类不存在")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2222)
