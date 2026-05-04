from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime
from pathlib import Path
import jinja2

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="网络书签管理器", description="一个简单的网络书签管理应用")

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

DATA_FILE = "bookmarks.json"

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

def load_bookmarks():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bookmarks(bookmarks):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=2)

def get_next_id(bookmarks):
    if not bookmarks:
        return 1
    return max(bookmark["id"] for bookmark in bookmarks) + 1

def get_bookmark_by_id(bookmark_id: int):
    bookmarks = load_bookmarks()
    for bookmark in bookmarks:
        if bookmark["id"] == bookmark_id:
            return bookmark
    return None

def render_template(template_name: str, **context):
    template = jinja_env.get_template(template_name)
    return template.render(**context)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    bookmarks = load_bookmarks()
    bookmarks.sort(key=lambda x: x["created_at"], reverse=True)
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
    bookmarks = load_bookmarks()
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    new_bookmark = {
        "id": get_next_id(bookmarks),
        "title": title,
        "url": url,
        "description": description or None,
        "tags": tags_list,
        "created_at": datetime.now().isoformat(),
        "updated_at": None
    }
    bookmarks.append(new_bookmark)
    save_bookmarks(bookmarks)
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
    bookmarks = load_bookmarks()
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    for i, bookmark in enumerate(bookmarks):
        if bookmark["id"] == bookmark_id:
            bookmarks[i]["title"] = title
            bookmarks[i]["url"] = url
            bookmarks[i]["description"] = description or None
            bookmarks[i]["tags"] = tags_list
            bookmarks[i]["updated_at"] = datetime.now().isoformat()
            save_bookmarks(bookmarks)
            return RedirectResponse(url="/", status_code=303)
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{bookmark_id}", response_class=RedirectResponse)
async def delete_bookmark_web(bookmark_id: int):
    bookmarks = load_bookmarks()
    for i, bookmark in enumerate(bookmarks):
        if bookmark["id"] == bookmark_id:
            del bookmarks[i]
            save_bookmarks(bookmarks)
            break
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
    bookmarks = load_bookmarks()
    new_bookmark = {
        "id": get_next_id(bookmarks),
        "title": bookmark.title,
        "url": bookmark.url,
        "description": bookmark.description,
        "tags": bookmark.tags,
        "created_at": datetime.now().isoformat(),
        "updated_at": None
    }
    bookmarks.append(new_bookmark)
    save_bookmarks(bookmarks)
    return new_bookmark

@app.put("/api/bookmarks/{bookmark_id}", response_model=Bookmark)
def update_bookmark(bookmark_id: int, bookmark_update: BookmarkUpdate):
    bookmarks = load_bookmarks()
    for i, bookmark in enumerate(bookmarks):
        if bookmark["id"] == bookmark_id:
            update_data = bookmark_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                bookmarks[i][key] = value
            bookmarks[i]["updated_at"] = datetime.now().isoformat()
            save_bookmarks(bookmarks)
            return bookmarks[i]
    raise HTTPException(status_code=404, detail="书签不存在")

@app.delete("/api/bookmarks/{bookmark_id}")
def delete_bookmark(bookmark_id: int):
    bookmarks = load_bookmarks()
    for i, bookmark in enumerate(bookmarks):
        if bookmark["id"] == bookmark_id:
            del bookmarks[i]
            save_bookmarks(bookmarks)
            return {"message": "书签已删除"}
    raise HTTPException(status_code=404, detail="书签不存在")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2222)
