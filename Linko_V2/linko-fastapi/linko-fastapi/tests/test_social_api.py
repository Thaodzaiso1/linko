"""Run: python -m pytest tests/test_social_api.py -q"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import social_api
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(social_api, "DATABASE_PATH", tmp_path / "social-test.db")
    with TestClient(app) as c:
        yield c


def headers(client, username="admin", password=None):
    password = password or ("admin123" if username == "admin" else "viewer123")
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


def test_endpoints_require_auth(client):
    assert client.get("/api/social/posts").status_code == 401
    assert client.get("/api/social/notifications").status_code == 401
    assert client.post("/api/social/posts", json={"content": "Hello"}).status_code == 401


def test_post_like_comment_and_delete(client):
    h = headers(client)
    result = client.post("/api/social/posts", json={"content": "  Thông báo nội bộ  "}, headers=h)
    assert result.status_code == 201
    assert result.json()["content"] == "Thông báo nội bộ"
    pid = result.json()["id"]
    liked = client.post(f"/api/social/posts/{pid}/like", headers=h).json()
    assert liked["liked_by_me"] and liked["likes_count"] == 1
    unliked = client.post(f"/api/social/posts/{pid}/like", headers=h).json()
    assert not unliked["liked_by_me"] and unliked["likes_count"] == 0
    comment = client.post(f"/api/social/posts/{pid}/comments", json={"content": "Rất hay!"}, headers=h)
    assert comment.status_code == 201
    assert client.get(f"/api/social/posts/{pid}/comments", headers=h).json()[0]["content"] == "Rất hay!"
    assert client.get("/api/social/summary", headers=h).json() == {"posts": 1, "comments": 1, "likes": 0}
    assert client.delete(f"/api/social/posts/{pid}", headers=h).status_code == 200
    assert client.get(f"/api/social/posts/{pid}/comments", headers=h).status_code == 404
    assert client.get("/api/social/summary", headers=h).json()["comments"] == 0


def test_cannot_delete_other_users_posts(client):
    admin = headers(client)
    viewer = headers(client, "viewer")
    pid = client.post("/api/social/posts", json={"content": "Thông điệp"}, headers=admin).json()["id"]
    assert client.delete(f"/api/social/posts/{pid}", headers=viewer).status_code == 403
    assert client.get("/api/social/posts", headers=admin).json()["total"] == 1


def test_notifications_private_and_read_state(client):
    admin = headers(client)
    viewer = headers(client, "viewer")
    pid = client.post("/api/social/posts", json={"content": "Cập nhật"}, headers=admin).json()["id"]
    client.post(f"/api/social/posts/{pid}/like", headers=viewer)
    client.post(f"/api/social/posts/{pid}/comments", json={"content": "Đã nhận"}, headers=viewer)
    owner_notifications = client.get("/api/social/notifications", headers=admin).json()
    assert owner_notifications["unread"] == 2
    assert {n["kind"] for n in owner_notifications["items"]} == {"like", "comment"}
    assert client.get("/api/social/notifications", headers=viewer).json()["unread"] == 0
    assert client.post("/api/social/notifications/read", headers=admin).status_code == 200
    assert client.get("/api/social/notifications", headers=admin).json()["unread"] == 0


def test_validation_and_pagination(client):
    h = headers(client)
    for invalid in ("   ", "x" * 2001):
        assert client.post("/api/social/posts", json={"content": invalid}, headers=h).status_code == 422
    for idx in range(4):
        assert client.post("/api/social/posts", json={"content": f"Sự kiện số {idx}"}, headers=h).status_code == 201
    r = client.get("/api/social/posts?page=2&page_size=2&q=Sự kiện", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 4
    assert r.json()["pages"] == 2
    assert len(r.json()["items"]) == 2
    assert client.get("/api/social/posts?page_size=100", headers=h).status_code == 422


def test_sqlite_persists_after_reopening_client(client):
    h = headers(client)
    client.post("/api/social/posts", json={"content": "Một bài lưu lâu dài"}, headers=h)
    with social_api.db() as connection:
        row = connection.execute("SELECT content FROM posts LIMIT 1").fetchone()
    assert row["content"] == "Một bài lưu lâu dài"


def test_direct_messages_are_private(client):
    admin = headers(client)
    viewer = headers(client, "viewer")
    sent = client.post("/api/social/messages", json={"to_username": "viewer", "content": "Xin chào!"}, headers=admin)
    assert sent.status_code == 201
    assert sent.json()["sender_username"] == "admin"
    assert len(client.get("/api/social/messages/viewer", headers=admin).json()) == 1
    assert len(client.get("/api/social/messages/admin", headers=viewer).json()) == 1
    assert client.get("/api/social/messages/manager", headers=viewer).json() == []
    peers = client.get("/api/social/messages/peers", headers=viewer).json()
    assert next(p for p in peers if p["username"] == "admin")["unread"] == 1
    assert client.post("/api/social/messages/admin/read", headers=viewer).status_code == 200
    assert next(p for p in client.get("/api/social/messages/peers", headers=viewer).json() if p["username"] == "admin")["unread"] == 0
    assert client.post("/api/social/messages", json={"to_username": "viewer", "content": "no"}, headers=viewer).status_code == 422
    assert client.post("/api/social/messages", json={"to_username": "nobody", "content": "hi"}, headers=admin).status_code == 422
    assert client.get("/api/social/messages/admin").status_code == 401


def test_openapi_and_existing_dashboard(client):
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/social/messages" in schema.json()["paths"]
    assert "/api/social/posts" in schema.json()["paths"]
    admin = headers(client)
    assert client.get("/api/dashboard/overview", headers=admin).status_code == 200
    assert client.get("/api/v1/social/posts", headers=admin).status_code == 200
