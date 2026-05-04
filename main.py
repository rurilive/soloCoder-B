from fastapi import FastAPI, HTTPException, Request, Form, Query
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

app = FastAPI(title="网络书签管理器", description="一个支持分类、搜索和层级结构的网络书签管理应用")

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)

BOOKMARKS_FILE = "bookmarks.json"
CATEGORIES_FILE = "categories.json"

class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None

class Category(CategoryBase):
    id: int
    created_at: str
    updated_at: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None

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

class BookmarkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    category_id: Optional[int] = None

def load_bookmarks():
    if not os.path.exists(BOOKMARKS_FILE):
        return []
    with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bookmarks(bookmarks):
    with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=2)

def load_categories():
    if not os.path.exists(CATEGORIES_FILE):
        default_categories = [
            {
                "id": 1,
                "name": "工作",
                "description": "工作相关的资源",
                "parent_id": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": None
            },
            {
                "id": 2,
                "name": "学习",
                "description": "学习资源",
                "parent_id": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": None
            },
            {
                "id": 3,
                "name": "娱乐",
                "description": "娱乐休闲",
                "parent_id": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": None
            }
        ]
        save_categories(default_categories)
        return default_categories
    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_categories(categories):
    with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

def get_next_id(items):
    if not items:
        return 1
    return max(item["id"] for item in items) + 1

def get_bookmark_by_id(bookmark_id: int):
    bookmarks = load_bookmarks()
    for bookmark in bookmarks:
        if bookmark["id"] == bookmark_id:
            return bookmark
    return None

def get_category_by_id(category_id: int):
    categories = load_categories()
    for category in categories:
        if category["id"] == category_id:
            return category
    return None

def get_category_children(category_id: int):
    categories = load_categories()
    return [c for c in categories if c["parent_id"] == category_id]

def get_category_hierarchy():
    categories = load_categories()
    category_map = {c["id"]: {**c, "children": [], "bookmarks": []} for c in categories}
    
    roots = []
    for cat in categories:
        if cat["parent_id"] is None:
            roots.append(category_map[cat["id"]])
        elif cat["parent_id"] in category_map:
            category_map[cat["parent_id"]]["children"].append(category_map[cat["id"]])
    
    bookmarks = load_bookmarks()
    for bookmark in bookmarks:
        cat_id = bookmark.get("category_id")
        if cat_id in category_map:
            category_map[cat_id]["bookmarks"].append(bookmark)
    
    return roots, category_map

def search_bookmarks(query: str = None, category_id: int = None, tags: List[str] = None):
    bookmarks = load_bookmarks()
    results = bookmarks
    
    if category_id is not None:
        results = [b for b in results if b.get("category_id") == category_id]
    
    if query:
        query_lower = query.lower()
        results = [
            b for b in results
            if query_lower in b["title"].lower()
            or query_lower in b["url"].lower()
            or query_lower in (b.get("description") or "").lower()
            or any(query_lower in tag.lower() for tag in b.get("tags", []))
        ]
    
    if tags:
        tags_lower = [t.lower() for t in tags]
        results = [
            b for b in results
            if any(t in [tag.lower() for tag in b.get("tags", [])] for t in tags_lower)
        ]
    
    return results

def render_template(template_name: str, **context):
    template = jinja_env.get_template(template_name)
    return template.render(**context)

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    q: Optional[str] = Query(None, description="搜索关键词"),
    category_id: Optional[int] = Query(None, description="分类ID过滤"),
    tag: Optional[List[str]] = Query(None, description="标签过滤")
):
    bookmarks = search_bookmarks(query=q, category_id=category_id, tags=tag)
    bookmarks.sort(key=lambda x: x["created_at"], reverse=True)
    
    categories = load_categories()
    category_hierarchy, category_map = get_category_hierarchy()
    
    all_tags = set()
    for bookmark in load_bookmarks():
        for tag_item in bookmark.get("tags", []):
            all_tags.add(tag_item)
    all_tags = sorted(list(all_tags))
    
    current_category = None
    if category_id:
        current_category = get_category_by_id(category_id)
    
    html_content = render_template(
        "index.html", 
        request=request, 
        bookmarks=bookmarks,
        categories=categories,
        category_hierarchy=category_hierarchy,
        category_map=category_map,
        all_tags=all_tags,
        current_category=current_category,
        search_query=q,
        selected_tags=tag or [],
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request):
    categories = load_categories()
    category_hierarchy, category_map = get_category_hierarchy()
    
    html_content = render_template(
        "categories.html",
        request=request,
        categories=categories,
        category_hierarchy=category_hierarchy,
        category_map=category_map,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.get("/categories/add", response_class=HTMLResponse)
async def add_category_form(request: Request):
    categories = load_categories()
    html_content = render_template(
        "category_form.html",
        request=request,
        categories=categories,
        category=None,
        is_edit=False,
        messages=[]
    )
    return HTMLResponse(content=html_content)

@app.post("/categories/add", response_class=RedirectResponse)
async def add_category(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None)
):
    categories = load_categories()
    
    if parent_id is not None and parent_id != 0:
        parent = get_category_by_id(parent_id)
        if not parent:
            parent_id = None
    else:
        parent_id = None
    
    new_category = {
        "id": get_next_id(categories),
        "name": name,
        "description": description or None,
        "parent_id": parent_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": None
    }
    categories.append(new_category)
    save_categories(categories)
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/categories/edit/{category_id}", response_class=HTMLResponse)
async def edit_category_form(request: Request, category_id: int):
    category = get_category_by_id(category_id)
    if not category:
        return RedirectResponse(url="/categories", status_code=303)
    
    categories = load_categories()
    categories = [c for c in categories if c["id"] != category_id]
    
    html_content = render_template(
        "category_form.html",
        request=request,
        categories=categories,
        category=category,
        is_edit=True,
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
    categories = load_categories()
    
    if parent_id is not None and parent_id != 0:
        if parent_id == category_id:
            parent_id = None
        else:
            parent = get_category_by_id(parent_id)
            if not parent:
                parent_id = None
    else:
        parent_id = None
    
    for i, category in enumerate(categories):
        if category["id"] == category_id:
            categories[i]["name"] = name
            categories[i]["description"] = description or None
            categories[i]["parent_id"] = parent_id
            categories[i]["updated_at"] = datetime.now().isoformat()
            save_categories(categories)
            break
    
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/categories/delete/{category_id}", response_class=RedirectResponse)
async def delete_category(category_id: int):
    categories = load_categories()
    
    bookmarks = load_bookmarks()
    for bookmark in bookmarks:
        if bookmark.get("category_id") == category_id:
            bookmark["category_id"] = None
    save_bookmarks(bookmarks)
    
    def update_children(parent_id: int, new_parent_id: int = None):
        for cat in categories:
            if cat["parent_id"] == parent_id:
                cat["parent_id"] = new_parent_id
    
    update_children(category_id)
    
    categories = [c for c in categories if c["id"] != category_id]
    save_categories(categories)
    
    return RedirectResponse(url="/categories", status_code=303)

@app.get("/add", response_class=HTMLResponse)
async def add_bookmark_form(request: Request):
    categories = load_categories()
    html_content = render_template("add.html", request=request, categories=categories, messages=[])
    return HTMLResponse(content=html_content)

@app.post("/add", response_class=RedirectResponse)
async def add_bookmark(
    title: str = Form(...),
    url: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None)
):
    bookmarks = load_bookmarks()
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    if category_id == 0:
        category_id = None
    
    new_bookmark = {
        "id": get_next_id(bookmarks),
        "title": title,
        "url": url,
        "description": description or None,
        "tags": tags_list,
        "category_id": category_id,
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
    
    categories = load_categories()
    html_content = render_template("edit.html", request=request, bookmark=bookmark, categories=categories, messages=[])
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
    bookmarks = load_bookmarks()
    tags_list = []
    if tags:
        tags_list = [tag.strip().lower() for tag in tags.split(",") if tag.strip()]
    
    if category_id == 0:
        category_id = None
    
    for i, bookmark in enumerate(bookmarks):
        if bookmark["id"] == bookmark_id:
            bookmarks[i]["title"] = title
            bookmarks[i]["url"] = url
            bookmarks[i]["description"] = description or None
            bookmarks[i]["tags"] = tags_list
            bookmarks[i]["category_id"] = category_id
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

@app.get("/api/categories", response_model=List[Category])
def get_categories():
    return load_categories()

@app.get("/api/categories/{category_id}", response_model=Category)
def get_category(category_id: int):
    category = get_category_by_id(category_id)
    if category:
        return category
    raise HTTPException(status_code=404, detail="分类不存在")

@app.post("/api/categories", response_model=Category)
def create_category(category: CategoryBase):
    categories = load_categories()
    new_category = {
        "id": get_next_id(categories),
        "name": category.name,
        "description": category.description,
        "parent_id": category.parent_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": None
    }
    categories.append(new_category)
    save_categories(categories)
    return new_category

@app.put("/api/categories/{category_id}", response_model=Category)
def update_category(category_id: int, category_update: CategoryUpdate):
    categories = load_categories()
    for i, category in enumerate(categories):
        if category["id"] == category_id:
            update_data = category_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                categories[i][key] = value
            categories[i]["updated_at"] = datetime.now().isoformat()
            save_categories(categories)
            return categories[i]
    raise HTTPException(status_code=404, detail="分类不存在")

@app.delete("/api/categories/{category_id}")
def delete_category_api(category_id: int):
    categories = load_categories()
    for i, category in enumerate(categories):
        if category["id"] == category_id:
            del categories[i]
            save_categories(categories)
            return {"message": "分类已删除"}
    raise HTTPException(status_code=404, detail="分类不存在")

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
        "category_id": bookmark.category_id,
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
    uvicorn.run(app, host="0.0.0.0", port=8888)
