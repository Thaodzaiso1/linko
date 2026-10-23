"""Linko social feed API backed by SQLite (independent from Oracle graph data).

Provides persistent posts, comments, likes and notifications for demo accounts.
All mutations are authenticated and use SQL parameters and server-side identity.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator

DATABASE_PATH = Path(os.getenv("LINKO_SOCIAL_DB", str(Path(__file__).with_name("linko_social.db")))).expanduser()
router = APIRouter(prefix="/api/social", tags=["Social"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def db():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_social_db() -> None:
    with db() as cx:
        cx.execute("PRAGMA journal_mode=WAL")
        cx.executescript("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_username TEXT NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                author_username TEXT NOT NULL,
                author_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS likes (
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (post_id, username)
            );
            CREATE TABLE IF NOT EXISTS post_bookmarks (
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (post_id, username)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient_username TEXT NOT NULL,
                actor_username TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                kind TEXT NOT NULL,
                post_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS direct_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_username TEXT NOT NULL,
                receiver_username TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_messages_participants ON direct_messages(sender_username, receiver_username, id DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_inbox ON direct_messages(receiver_username, is_read);
            CREATE INDEX IF NOT EXISTS idx_posts_newest ON posts(id DESC);
            CREATE INDEX IF NOT EXISTS idx_bookmarks_user ON post_bookmarks(username, post_id DESC);
            CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id, id);
            CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(recipient_username, is_read, id DESC);
        """)
        # Automatic migration for SQLite databases created by Linko V5.
        columns = {column["name"] for column in cx.execute("PRAGMA table_info(posts)")}
        if "updated_at" not in columns:
            cx.execute("ALTER TABLE posts ADD COLUMN updated_at TEXT")


class PostInput(BaseModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def trim(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nội dung không được để trống")
        return value


class CommentInput(BaseModel):
    content: str = Field(min_length=1, max_length=600)

    @field_validator("content")
    @classmethod
    def trim(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Bình luận không được để trống")
        return value


def _post(cx: sqlite3.Connection, post_id: int, username: str):
    row = cx.execute("""
        SELECT p.*, (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS likes_count,
          (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comments_count,
          EXISTS(SELECT 1 FROM likes l WHERE l.post_id=p.id AND l.username=?) AS liked_by_me,
          EXISTS(SELECT 1 FROM post_bookmarks b WHERE b.post_id=p.id AND b.username=?) AS bookmarked_by_me
        FROM posts p WHERE p.id=?
    """, (username, username, post_id)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Bài viết không tồn tại")
    post = dict(row)
    post["liked_by_me"] = bool(post["liked_by_me"])
    post["bookmarked_by_me"] = bool(post["bookmarked_by_me"])
    return post


def _notification(cx: sqlite3.Connection, recipient: str, actor: dict, kind: str, post_id: int, message: str):
    if actor["username"] == recipient:
        return
    cx.execute("""
        INSERT INTO notifications
          (recipient_username, actor_username, actor_name, kind, post_id, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (recipient, actor["username"], actor["full_name"], kind, post_id, message, _now()))


class DirectMessageInput(BaseModel):
    to_username: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def trim_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tin nhắn không được để trống")
        return value


def mount_social_routes(app, require_user: Callable[[Request], dict], users: dict[str, dict]) -> None:
    """Mount once; dependency supplied by main app's authentication helper."""

    @router.get("/posts")
    def list_posts(request: Request, page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=30),
                   q: str = Query("", max_length=100), view: Literal["all", "mine", "saved"] = "all"):
        user = require_user(request)
        q = q.strip()
        conditions = []
        params: list = []
        if q:
            escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            conditions.append("p.content LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        if view == "mine":
            conditions.append("p.author_username=?")
            params.append(user["username"])
        elif view == "saved":
            conditions.append("EXISTS (SELECT 1 FROM post_bookmarks b WHERE b.post_id=p.id AND b.username=?)")
            params.append(user["username"])
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        with db() as cx:
            total = cx.execute(f"SELECT COUNT(*) FROM posts p {where_clause}", params).fetchone()[0]
            rows = cx.execute(f"""
                SELECT p.*, (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS likes_count,
                   (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comments_count,
                   EXISTS(SELECT 1 FROM likes l WHERE l.post_id=p.id AND l.username=?) AS liked_by_me,
                   EXISTS(SELECT 1 FROM post_bookmarks b WHERE b.post_id=p.id AND b.username=?) AS bookmarked_by_me
                FROM posts p {where_clause}
                ORDER BY p.id DESC LIMIT ? OFFSET ?
            """, [user["username"], user["username"], *params, page_size, (page - 1) * page_size]).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            item["liked_by_me"] = bool(item["liked_by_me"])
            item["bookmarked_by_me"] = bool(item["bookmarked_by_me"])
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "pages": (total + page_size - 1)//page_size, "view": view}

    @router.post("/posts", status_code=201)
    def create_post(body: PostInput, request: Request):
        user = require_user(request)
        with db() as cx:
            cur = cx.execute("INSERT INTO posts (author_username, author_name, content, created_at) VALUES (?, ?, ?, ?)",
                             (user["username"], user["full_name"], body.content, _now()))
            result = _post(cx, cur.lastrowid, user["username"])
        return result

    @router.put("/posts/{post_id}")
    def edit_post(post_id: int, body: PostInput, request: Request):
        user = require_user(request)
        with db() as cx:
            existing = cx.execute("SELECT author_username FROM posts WHERE id=?", (post_id,)).fetchone()
            if not existing:
                raise HTTPException(404, "Bài viết không tồn tại")
            if existing["author_username"] != user["username"]:
                raise HTTPException(403, "Chỉ tác giả được sửa bài viết")
            cx.execute("UPDATE posts SET content=?, updated_at=? WHERE id=?", (body.content, _now(), post_id))
            return _post(cx, post_id, user["username"])

    @router.delete("/posts/{post_id}")
    def delete_post(post_id: int, request: Request):
        user = require_user(request)
        with db() as cx:
            row = cx.execute("SELECT author_username FROM posts WHERE id=?", (post_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "Bài viết không tồn tại")
            if row["author_username"] != user["username"] and user["role"] != "admin":
                raise HTTPException(403, "Chỉ tác giả hoặc quản trị viên được xóa bài viết")
            cx.execute("DELETE FROM posts WHERE id=?", (post_id,))
            cx.execute("DELETE FROM notifications WHERE post_id=?", (post_id,))
        return {"ok": True}

    @router.post("/posts/{post_id}/like")
    def toggle_like(post_id: int, request: Request):
        user = require_user(request)
        with db() as cx:
            row = cx.execute("SELECT author_username FROM posts WHERE id=?", (post_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Bài viết không tồn tại")
            old = cx.execute("SELECT 1 FROM likes WHERE post_id=? AND username=?", (post_id, user["username"])).fetchone()
            if old:
                cx.execute("DELETE FROM likes WHERE post_id=? AND username=?", (post_id, user["username"]))
            else:
                cx.execute("INSERT INTO likes (post_id, username, created_at) VALUES (?, ?, ?)", (post_id, user["username"], _now()))
                _notification(cx, row["author_username"], user, "like", post_id, "đã thích bài viết của bạn")
            result = _post(cx, post_id, user["username"])
        return {"likes_count": result["likes_count"], "liked_by_me": bool(result["liked_by_me"])}

    @router.post("/posts/{post_id}/bookmark")
    def toggle_bookmark(post_id: int, request: Request):
        user = require_user(request)
        with db() as cx:
            _post(cx, post_id, user["username"])
            was_saved = cx.execute("SELECT 1 FROM post_bookmarks WHERE post_id=? AND username=?",
                                   (post_id, user["username"])).fetchone()
            if was_saved:
                cx.execute("DELETE FROM post_bookmarks WHERE post_id=? AND username=?", (post_id, user["username"]))
            else:
                cx.execute("INSERT INTO post_bookmarks(post_id, username, created_at) VALUES (?, ?, ?)",
                           (post_id, user["username"], _now()))
        return {"post_id": post_id, "bookmarked_by_me": not bool(was_saved)}

    @router.get("/posts/{post_id}/comments")
    def list_comments(post_id: int, request: Request, limit: int = Query(50, ge=1, le=100)):
        user = require_user(request)
        with db() as cx:
            _post(cx, post_id, user["username"])
            rows = cx.execute("SELECT * FROM comments WHERE post_id=? ORDER BY id DESC LIMIT ?", (post_id, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    @router.post("/posts/{post_id}/comments", status_code=201)
    def add_comment(post_id: int, body: CommentInput, request: Request):
        user = require_user(request)
        with db() as cx:
            post = cx.execute("SELECT author_username FROM posts WHERE id=?", (post_id,)).fetchone()
            if not post:
                raise HTTPException(404, "Bài viết không tồn tại")
            cur = cx.execute("""INSERT INTO comments (post_id, author_username, author_name, content, created_at)
                VALUES (?, ?, ?, ?, ?)""", (post_id, user["username"], user["full_name"], body.content, _now()))
            _notification(cx, post["author_username"], user, "comment", post_id, "đã bình luận về bài viết của bạn")
            result = cx.execute("SELECT * FROM comments WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(result)

    @router.delete("/comments/{comment_id}")
    def delete_comment(comment_id: int, request: Request):
        user = require_user(request)
        with db() as cx:
            row = cx.execute("SELECT author_username, post_id FROM comments WHERE id=?", (comment_id,)).fetchone()
            if not row:
                raise HTTPException(404, "Bình luận không tồn tại")
            if row["author_username"] != user["username"] and user["role"] != "admin":
                raise HTTPException(403, "Chỉ tác giả hoặc quản trị viên được xóa bình luận")
            cx.execute("DELETE FROM comments WHERE id=?", (comment_id,))
            return {"ok": True, "post_id": row["post_id"]}

    @router.get("/notifications")
    def list_notifications(request: Request, limit: int = Query(20, ge=1, le=50)):
        user = require_user(request)
        with db() as cx:
            rows = cx.execute("SELECT * FROM notifications WHERE recipient_username=? ORDER BY id DESC LIMIT ?",
                              (user["username"], limit)).fetchall()
            unread = cx.execute("SELECT COUNT(*) FROM notifications WHERE recipient_username=? AND is_read=0",
                                (user["username"],)).fetchone()[0]
        return {"items": [dict(row) for row in rows], "unread": unread}

    @router.post("/notifications/read")
    def mark_notifications_read(request: Request):
        user = require_user(request)
        with db() as cx:
            cx.execute("UPDATE notifications SET is_read=1 WHERE recipient_username=?", (user["username"],))
        return {"ok": True, "unread": 0}

    @router.post("/notifications/{notification_id}/read")
    def mark_one_notification_read(notification_id: int, request: Request):
        user = require_user(request)
        with db() as cx:
            result = cx.execute("UPDATE notifications SET is_read=1 WHERE id=? AND recipient_username=?",
                                (notification_id, user["username"]))
            if result.rowcount == 0:
                raise HTTPException(404, "Thông báo không tồn tại")
            unread = cx.execute("SELECT COUNT(*) FROM notifications WHERE recipient_username=? AND is_read=0",
                                (user["username"],)).fetchone()[0]
        return {"ok": True, "unread": unread}

    @router.get("/unread")
    def unread_totals(request: Request):
        user = require_user(request)
        with db() as cx:
            notifications = cx.execute("SELECT COUNT(*) FROM notifications WHERE recipient_username=? AND is_read=0",
                                       (user["username"],)).fetchone()[0]
            messages = cx.execute("SELECT COUNT(*) FROM direct_messages WHERE receiver_username=? AND is_read=0",
                                  (user["username"],)).fetchone()[0]
        return {"notifications": notifications, "messages": messages, "total": notifications + messages}

    @router.get("/summary")
    def social_summary(request: Request):
        require_user(request)
        with db() as cx:
            return {"posts": cx.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
                    "comments": cx.execute("SELECT COUNT(*) FROM comments").fetchone()[0],
                    "likes": cx.execute("SELECT COUNT(*) FROM likes").fetchone()[0]}

    # Demo direct messages are scoped to authenticated application accounts.
    # Messages do NOT target the employee graph: those records have no login identity.
    @router.get("/messages/peers")
    def message_peers(request: Request):
        current = require_user(request)["username"]
        with db() as cx:
            result = []
            for key, info in users.items():
                if key == current:
                    continue
                latest = cx.execute("""
                    SELECT content, created_at FROM direct_messages
                    WHERE (sender_username=? AND receiver_username=?)
                       OR (sender_username=? AND receiver_username=?)
                    ORDER BY id DESC LIMIT 1
                """, (current, key, key, current)).fetchone()
                unread = cx.execute("""
                    SELECT COUNT(*) FROM direct_messages
                    WHERE sender_username=? AND receiver_username=? AND is_read=0
                """, (key, current)).fetchone()[0]
                result.append({"username": key, "full_name": info["full_name"], "role": info["role"],
                               "last_message": latest["content"] if latest else None,
                               "last_at": latest["created_at"] if latest else None, "unread": unread})
        return sorted(result, key=lambda peer: peer["last_at"] or "", reverse=True)

    @router.get("/messages/search")
    def search_messages(request: Request, q: str = Query(min_length=1, max_length=100),
                        peer: str | None = Query(None, max_length=50), limit: int = Query(30, ge=1, le=50)):
        current = require_user(request)["username"]
        q = q.strip()
        if not q:
            raise HTTPException(422, "Từ khóa không được để trống")
        if peer is not None and (peer not in users or peer == current):
            raise HTTPException(404, "Không tìm thấy tài khoản trò chuyện")
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params: list = [current, current, f"%{escaped}%"]
        peer_filter = ""
        if peer is not None:
            peer_filter = "AND (sender_username=? OR receiver_username=?)"
            params.extend([peer, peer])
        with db() as cx:
            rows = cx.execute(f"""
                SELECT * FROM direct_messages
                WHERE (sender_username=? OR receiver_username=?) AND content LIKE ? ESCAPE '\\'
                {peer_filter} ORDER BY id DESC LIMIT ?
            """, [*params, limit]).fetchall()
        return [dict(row) for row in rows]

    @router.get("/messages/{peer}")
    def direct_messages(peer: str, request: Request, limit: int = Query(50, ge=1, le=100),
                        before_id: int | None = Query(None, ge=1)):
        current = require_user(request)["username"]
        if peer not in users or peer == current:
            raise HTTPException(404, "Không tìm thấy tài khoản trò chuyện")
        with db() as cx:
            rows = cx.execute("""SELECT * FROM direct_messages WHERE
                ((sender_username=? AND receiver_username=?) OR (sender_username=? AND receiver_username=?))
                AND (? IS NULL OR id < ?)
                ORDER BY id DESC LIMIT ?""", (current, peer, peer, current, before_id, before_id, limit)).fetchall()
        return [dict(m) for m in reversed(rows)]

    @router.post("/messages", status_code=201)
    def send_direct_message(body: DirectMessageInput, request: Request):
        user = require_user(request)
        receiver = body.to_username.strip()
        if receiver not in users or receiver == user["username"]:
            raise HTTPException(422, "Tài khoản nhận không hợp lệ")
        with db() as cx:
            cur = cx.execute("""INSERT INTO direct_messages (sender_username, receiver_username, content, created_at)
                VALUES (?, ?, ?, ?)""", (user["username"], receiver, body.content, _now()))
            result = cx.execute("SELECT * FROM direct_messages WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(result)

    @router.post("/messages/{peer}/read")
    def read_direct_messages(peer: str, request: Request):
        user = require_user(request)
        if peer not in users or peer == user["username"]:
            raise HTTPException(404, "Không tìm thấy tài khoản trò chuyện")
        with db() as cx:
            cx.execute("""UPDATE direct_messages SET is_read=1
                WHERE sender_username=? AND receiver_username=? AND is_read=0""",
                (peer, user["username"]))
        return {"ok": True}

    app.include_router(router)
