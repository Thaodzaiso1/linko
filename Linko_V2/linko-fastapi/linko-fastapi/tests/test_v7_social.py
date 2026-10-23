"""V7 tests: saved posts and private full-text message search.
Run: python -m pytest tests -q
"""
import sqlite3

import pytest
from fastapi.testclient import TestClient

import social_api
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(social_api, 'DATABASE_PATH', tmp_path / 'social-v7.db')
    with TestClient(app) as c:
        yield c


def login(client, username):
    passwords = {'admin': 'admin123', 'viewer': 'viewer123', 'manager': 'manager123'}
    response = client.post('/api/auth/login', json={'username': username, 'password': passwords[username]})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['token']}"}


def test_bookmark_private_toggle_and_saved_feed(client):
    admin, viewer = login(client, 'admin'), login(client, 'viewer')
    own = client.post('/api/social/posts', json={'content': 'Admin item'}, headers=admin).json()['id']
    other = client.post('/api/social/posts', json={'content': 'Viewer item'}, headers=viewer).json()['id']
    assert client.post(f'/api/social/posts/{own}/bookmark').status_code == 401
    assert client.post('/api/social/posts/999999/bookmark', headers=admin).status_code == 404
    result = client.post(f'/api/social/posts/{other}/bookmark', headers=admin)
    assert result.status_code == 200
    assert result.json()['bookmarked_by_me'] is True
    saved = client.get('/api/social/posts?view=saved', headers=admin).json()
    assert saved['total'] == 1 and saved['items'][0]['id'] == other
    assert saved['items'][0]['bookmarked_by_me'] is True
    assert client.get('/api/social/posts?view=saved', headers=viewer).json()['total'] == 0
    mine = client.get('/api/social/posts?view=mine', headers=admin).json()
    assert mine['total'] == 1 and mine['items'][0]['id'] == own
    assert client.get('/api/social/posts?view=invalid', headers=admin).status_code == 422
    assert client.post(f'/api/social/posts/{other}/bookmark', headers=admin).json()['bookmarked_by_me'] is False
    assert client.get('/api/social/posts?view=saved', headers=admin).json()['total'] == 0


def test_bookmarks_survive_restart_and_cascade_delete(client):
    admin = login(client, 'admin')
    post_id = client.post('/api/social/posts', json={'content': 'Persisted'}, headers=admin).json()['id']
    client.post(f'/api/social/posts/{post_id}/bookmark', headers=admin)
    social_api.initialize_social_db()
    assert client.get('/api/social/posts?view=saved', headers=admin).json()['total'] == 1
    client.delete(f'/api/social/posts/{post_id}', headers=admin)
    with social_api.db() as cx:
        assert cx.execute('SELECT COUNT(*) FROM post_bookmarks').fetchone()[0] == 0


def test_message_search_is_private_and_peer_scoped(client):
    admin, viewer, manager = (login(client, name) for name in ['admin', 'viewer', 'manager'])
    client.post('/api/social/messages', json={'to_username': 'viewer', 'content': 'Dự án phòng thiết kế A'}, headers=admin)
    client.post('/api/social/messages', json={'to_username': 'manager', 'content': 'Dự án phòng thiết kế B'}, headers=admin)
    client.post('/api/social/messages', json={'to_username': 'manager', 'content': 'Bí mật giám đốc'}, headers=viewer)
    assert client.get('/api/social/messages/search?q=Dự%20án').status_code == 401
    result = client.get('/api/social/messages/search', params={'q': 'Dự án'}, headers=admin)
    assert result.status_code == 200 and len(result.json()) == 2
    viewer_search = client.get('/api/social/messages/search', params={'q': 'Dự án'}, headers=viewer)
    assert len(viewer_search.json()) == 1
    manager_search = client.get('/api/social/messages/search', params={'q': 'Dự án'}, headers=manager)
    assert len(manager_search.json()) == 1
    peer_results = client.get('/api/social/messages/search', params={'q': 'Dự án', 'peer': 'viewer'}, headers=admin)
    assert len(peer_results.json()) == 1 and peer_results.json()[0]['receiver_username'] == 'viewer'
    assert client.get('/api/social/messages/search', params={'q': 'Bí mật', 'peer': 'viewer'}, headers=admin).json() == []
    assert client.get('/api/social/messages/search', params={'q': 'Dự án', 'peer': 'nobody'}, headers=admin).status_code == 404
    assert client.get('/api/social/messages/search', params={'q': ' '}, headers=admin).status_code == 422


def test_search_escapes_sql_wildcards(client):
    admin = login(client, 'admin')
    client.post('/api/social/posts', json={'content': 'Kiểm thử 100% OK'}, headers=admin)
    client.post('/api/social/posts', json={'content': 'Kiểm thử 100a OK'}, headers=admin)
    assert client.get('/api/social/posts', params={'q': '%'}, headers=admin).json()['total'] == 1
    client.post('/api/social/messages', json={'to_username': 'viewer', 'content': 'A_B'}, headers=admin)
    client.post('/api/social/messages', json={'to_username': 'viewer', 'content': 'ACB'}, headers=admin)
    assert len(client.get('/api/social/messages/search', params={'q': '_'}, headers=admin).json()) == 1


def test_migration_from_v6_preserves_existing_posts(tmp_path, monkeypatch):
    target = tmp_path / 'upgrade.db'
    with sqlite3.connect(target) as cx:
        cx.execute('CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, author_username TEXT NOT NULL, author_name TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT)')
        cx.execute("INSERT INTO posts (author_username, author_name, content, created_at) VALUES ('admin','Admin','V6 content','2026-10-18')")
    monkeypatch.setattr(social_api, 'DATABASE_PATH', target)
    social_api.initialize_social_db()
    with social_api.db() as cx:
        assert cx.execute('SELECT content FROM posts').fetchone()['content'] == 'V6 content'
        assert cx.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='post_bookmarks'").fetchone()
