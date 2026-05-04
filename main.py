from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime

app = FastAPI(title="网络书签管理器", description="一个简单的网络书签管理应用")

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

@app.get("/")
def read_root():
    return {"message": "欢迎使用网络书签管理器", "docs": "/docs"}

@app.get("/api/bookmarks", response_model=List[Bookmark])
def get_bookmarks():
    return load_bookmarks()

@app.get("/api/bookmarks/{bookmark_id}", response_model=Bookmark)
def get_bookmark(bookmark_id: int):
    bookmarks = load_bookmarks()
    for bookmark in bookmarks:
        if bookmark["id"] == bookmark_id:
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
