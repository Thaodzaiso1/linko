"""Linko V6 regression tests: authorization, edit/delete, notifications, paging and migration."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

import social_api
import main
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(social_api, "DATABASE_PATH", tmp_path / "upgrade.db")
    # Restore the shared in-memory mock organization when a test creates a record.
    depts = [dict(row) for row in main.MOCK_DEPARTMENTS]
    projects = [dict(row) for row in main.MOCK_PROJECTS]
    with TestClient(app) as client:
        yield client
    main.MOCK_DEPARTMENTS[:] = depts
    main.MOCK_PROJECTS[:] = projects


def login(client, username):
    password = {"admin": "admin123", "manager": "manager123", "viewer": "viewer123"}[username]
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_public_private_and_v1_protection(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/api/employees").status_code == 401
    assert client.get("/api/v1/employees").status_code == 401
    assert client.get("/api/metrics").status_code == 401
    token = login(client, "viewer")
    assert client.get("/api/v1/employees", headers=token).status_code == 200
    assert client.get("/api/metrics", headers=token).status_code == 200


def test_post_edit_permissions_and_validation(client):
    admin, viewer = login(client, "admin"), login(client, "viewer")
    post_id = client.post("/api/social/posts", json={"content": "Original"}, headers=admin).json()["id"]
    assert client.put(f"/api/social/posts/{post_id}", json={"content": "Illegal"}, headers=viewer).status_code == 403
    assert client.put(f"/api/social/posts/{post_id}", json={"content": "  "}, headers=admin).status_code == 422
    updated = client.put(f"/api/social/posts/{post_id}", json={"content": "  Updated  "}, headers=admin)
    assert updated.status_code == 200
    assert updated.json()["content"] == "Updated"
    assert updated.json()["updated_at"]
    assert client.put("/api/social/posts/999999", json={"content": "Unknown"}, headers=admin).status_code == 404


def test_comment_delete_owner_and_admin(client):
    admin, viewer = login(client, "admin"), login(client, "viewer")
    pid = client.post("/api/social/posts", json={"content": "Hello"}, headers=admin).json()["id"]
    comment = client.post(f"/api/social/posts/{pid}/comments", json={"content": "From viewer"}, headers=viewer).json()
    assert client.delete(f"/api/social/comments/{comment['id']}", headers=admin).status_code == 200
    assert client.delete(f"/api/social/comments/{comment['id']}", headers=viewer).status_code == 404
    comment = client.post(f"/api/social/posts/{pid}/comments", json={"content": "Admin comment"}, headers=admin).json()
    assert client.delete(f"/api/social/comments/{comment['id']}", headers=viewer).status_code == 403
    assert client.delete(f"/api/social/comments/{comment['id']}", headers=admin).status_code == 200
    assert client.get("/api/social/posts", headers=admin).json()["items"][0]["comments_count"] == 0


def test_notifications_read_individually_and_unread_counts(client):
    admin, viewer = login(client, "admin"), login(client, "viewer")
    pid = client.post("/api/social/posts", json={"content": "Notice"}, headers=admin).json()["id"]
    client.post(f"/api/social/posts/{pid}/like", headers=viewer)
    client.post(f"/api/social/posts/{pid}/comments", json={"content": "Hi"}, headers=viewer)
    client.post("/api/social/messages", json={"to_username": "admin", "content": "ping"}, headers=viewer)
    counts = client.get("/api/social/unread", headers=admin).json()
    assert counts == {"notifications": 2, "messages": 1, "total": 3}
    n = client.get("/api/social/notifications", headers=admin).json()["items"][0]
    assert client.post(f"/api/social/notifications/{n['id']}/read", headers=viewer).status_code == 404
    assert client.post(f"/api/social/notifications/{n['id']}/read", headers=admin).json()["unread"] == 1
    assert client.get("/api/social/unread", headers=admin).json()["notifications"] == 1
    client.post("/api/social/messages/viewer/read", headers=admin)
    assert client.get("/api/social/unread", headers=admin).json()["messages"] == 0


def test_message_history_cursor(client):
    admin, viewer = login(client, "admin"), login(client, "viewer")
    for number in range(65):
        assert client.post("/api/social/messages", json={"to_username": "viewer", "content": f"m-{number}"}, headers=admin).status_code == 201
    last = client.get("/api/social/messages/admin?limit=50", headers=viewer).json()
    assert len(last) == 50 and last[-1]["content"] == "m-64"
    older = client.get(f"/api/social/messages/admin?limit=50&before_id={last[0]['id']}", headers=viewer).json()
    assert len(older) == 15 and older[0]["content"] == "m-0"
    assert older[-1]["id"] < last[0]["id"]
    assert client.get("/api/social/messages/admin?before_id=0", headers=viewer).status_code == 422


def test_org_permissions_and_integrity(client):
    viewer, manager, admin = login(client, "viewer"), login(client, "manager"), login(client, "admin")
    body = {"department_name": "Phòng mới", "location": "TP.HCM"}
    assert client.post("/api/departments", json=body, headers=viewer).status_code == 403
    created = client.post("/api/departments", json=body, headers=manager)
    assert created.status_code == 201
    dept_id = created.json()["department_id"]
    assert client.delete(f"/api/departments/{dept_id}", headers=manager).status_code == 403
    assert client.post("/api/projects", json={"project_name": "X", "status": "ACTIVE"}, headers=manager).status_code == 422
    assert client.post("/api/projects", json={"project_name": "Project X", "department_id": 12345}, headers=manager).status_code == 422
    project = client.post("/api/projects", json={"project_name": "Project X", "department_id": dept_id}, headers=manager)
    assert project.status_code == 201
    assert client.delete(f"/api/departments/{dept_id}", headers=admin).status_code == 409
    assert client.delete(f"/api/projects/{project.json()['project_id']}", headers=admin).status_code == 200
    assert client.delete(f"/api/departments/{dept_id}", headers=admin).status_code == 200


def test_migration_from_v5_schema(tmp_path, monkeypatch):
    target = tmp_path / "legacy.db"
    with sqlite3.connect(target) as cx:
        cx.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, author_username TEXT NOT NULL, author_name TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL)")
        cx.execute("INSERT INTO posts (author_username, author_name, content, created_at) VALUES ('admin','Admin','Legacy','2026-10-18')")
    monkeypatch.setattr(social_api, "DATABASE_PATH", target)
    social_api.initialize_social_db()
    with social_api.db() as cx:
        columns = {col['name'] for col in cx.execute("PRAGMA table_info(posts)")}
        assert "updated_at" in columns
        assert cx.execute("SELECT content FROM posts").fetchone()['content'] == 'Legacy'


def test_login_throttles_repeated_invalid_passwords(client):
    main._LOGIN_FAILURES.clear()
    try:
        for _ in range(main.LOGIN_MAX_ATTEMPTS):
            assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 429
    finally:
        main._LOGIN_FAILURES.clear()
    assert client.post("/api/auth/login", json={"username": "admin", "password": "admin123"}).status_code == 200


def test_oracle_org_write_does_not_silently_change_mock(client, monkeypatch):
    admin = login(client, "admin")
    before = len(main.MOCK_DEPARTMENTS)
    class FakePool:
        def close(self):
            pass
    monkeypatch.setattr(main, "_pool", FakePool())
    monkeypatch.setattr(main, "USE_MOCK", False)
    response = client.post("/api/departments", json={"department_name": "Oracle Dept"}, headers=admin)
    assert response.status_code == 501
    assert len(main.MOCK_DEPARTMENTS) == before
