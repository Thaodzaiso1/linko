"""
Linko API — FastAPI backend
Hệ thống mạng xã hội nội bộ doanh nghiệp
Đề tài 17 · Nhóm 13 · Oracle Database 23ai · SQL Property Graph
"""

from __future__ import annotations

import os
import time
import uuid
import hmac
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request, APIRouter, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
USE_MOCK = os.getenv("USE_MOCK", "true").lower() in ("1", "true", "yes")
ORACLE_USER = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "OraclePassword123")
ORACLE_CONNECT = os.getenv("ORACLE_CONNECT_STRING", "localhost:1521/lab04")
PORT = int(os.getenv("PORT", "8000"))
SESSION_TTL_SECONDS = max(300, int(os.getenv("SESSION_TTL_SECONDS", "28800")))

# ---------------------------------------------------------------------------
# Mock data (khớp 02_sample_data.sql)
# ---------------------------------------------------------------------------
MOCK_EMPLOYEES = [
    {"employee_id": 1, "full_name": "Nguyễn Văn An", "email": "an.nguyen@company.vn", "title": "Tổng Giám đốc", "department_id": 1, "department_name": "Ban Giám đốc", "status": "ACTIVE"},
    {"employee_id": 2, "full_name": "Trần Thị Bình", "email": "binh.tran@company.vn", "title": "Phó Tổng Giám đốc", "department_id": 1, "department_name": "Ban Giám đốc", "status": "ACTIVE"},
    {"employee_id": 3, "full_name": "Lê Minh Cường", "email": "cuong.le@company.vn", "title": "Giám đốc Công nghệ", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 4, "full_name": "Phạm Thu Dung", "email": "dung.pham@company.vn", "title": "Giám đốc Sản phẩm", "department_id": 3, "department_name": "Phòng Sản phẩm", "status": "ACTIVE"},
    {"employee_id": 5, "full_name": "Hoàng Văn Em", "email": "em.hoang@company.vn", "title": "Giám đốc Marketing", "department_id": 4, "department_name": "Phòng Marketing", "status": "ACTIVE"},
    {"employee_id": 6, "full_name": "Võ Thị Phương", "email": "phuong.vo@company.vn", "title": "Trưởng phòng Backend", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 7, "full_name": "Đặng Quốc Huy", "email": "huy.dang@company.vn", "title": "Trưởng phòng Frontend", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 8, "full_name": "Bùi Minh Tuấn", "email": "tuan.bui@company.vn", "title": "Tech Lead", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 9, "full_name": "Ngô Thị Lan", "email": "lan.ngo@company.vn", "title": "Senior Backend Dev", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 10, "full_name": "Đỗ Văn Khoa", "email": "khoa.do@company.vn", "title": "Senior Frontend Dev", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 11, "full_name": "Lý Thị Mai", "email": "mai.ly@company.vn", "title": "Backend Developer", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 12, "full_name": "Trương Văn Nam", "email": "nam.truong@company.vn", "title": "Frontend Developer", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 13, "full_name": "Phan Thị Oanh", "email": "oanh.phan@company.vn", "title": "DevOps Engineer", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 14, "full_name": "Vũ Minh Phát", "email": "phat.vu@company.vn", "title": "QA Engineer", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 15, "full_name": "Đinh Thị Quỳnh", "email": "quynh.dinh@company.vn", "title": "Data Engineer", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 20, "full_name": "Ngô Văn Vinh", "email": "vinh.ngo@company.vn", "title": "Junior Backend", "department_id": 2, "department_name": "Phòng Công nghệ", "status": "ACTIVE"},
    {"employee_id": 23, "full_name": "Nguyễn Thị Ánh", "email": "anh.nguyen@company.vn", "title": "Product Manager", "department_id": 3, "department_name": "Phòng Sản phẩm", "status": "ACTIVE"},
    {"employee_id": 24, "full_name": "Phạm Văn Bảo", "email": "bao.pham@company.vn", "title": "Product Owner", "department_id": 3, "department_name": "Phòng Sản phẩm", "status": "ACTIVE"},
    {"employee_id": 50, "full_name": "Hoàng Văn Khoa", "email": "khoa.hoang@company.vn", "title": "Giám đốc Chi nhánh HN", "department_id": 9, "department_name": "Chi nhánh Hà Nội", "status": "ACTIVE"},
    {"employee_id": 52, "full_name": "Võ Văn Nam", "email": "nam.vo@company.vn", "title": "Tech Lead HN", "department_id": 9, "department_name": "Chi nhánh Hà Nội", "status": "ACTIVE"},
    {"employee_id": 53, "full_name": "Bùi Thị Oanh", "email": "oanh.bui@company.vn", "title": "Developer HN", "department_id": 9, "department_name": "Chi nhánh Hà Nội", "status": "ACTIVE"},
    {"employee_id": 56, "full_name": "Trương Văn Rồng", "email": "rong.truong@company.vn", "title": "Giám đốc Chi nhánh DN", "department_id": 10, "department_name": "Chi nhánh Đà Nẵng", "status": "ACTIVE"},
    {"employee_id": 58, "full_name": "Vũ Văn Tâm", "email": "tam.vu@company.vn", "title": "Developer DN", "department_id": 10, "department_name": "Chi nhánh Đà Nẵng", "status": "ACTIVE"},
    {"employee_id": 63, "full_name": "Hồ Thị Ánh", "email": "anh.ho@company.vn", "title": "R&D Manager", "department_id": 12, "department_name": "Trung tâm R&D", "status": "ACTIVE"},
    {"employee_id": 64, "full_name": "Ngô Văn Bảo", "email": "bao.ngo@company.vn", "title": "AI Researcher", "department_id": 12, "department_name": "Trung tâm R&D", "status": "ACTIVE"},
]

MOCK_DEPARTMENTS = [
    {"department_id": 1, "department_name": "Ban Giám đốc", "location": "Tầng 10 - HQ"},
    {"department_id": 2, "department_name": "Phòng Công nghệ", "location": "Tầng 7 - HQ"},
    {"department_id": 3, "department_name": "Phòng Sản phẩm", "location": "Tầng 6 - HQ"},
    {"department_id": 4, "department_name": "Phòng Marketing", "location": "Tầng 5 - HQ"},
    {"department_id": 5, "department_name": "Phòng Nhân sự", "location": "Tầng 4 - HQ"},
    {"department_id": 9, "department_name": "Chi nhánh Hà Nội", "location": "Hà Nội"},
    {"department_id": 10, "department_name": "Chi nhánh Đà Nẵng", "location": "Đà Nẵng"},
    {"department_id": 12, "department_name": "Trung tâm R&D", "location": "Tầng 8 - HQ"},
]

MOCK_PROJECTS = [
    {"project_id": 1, "project_name": "Nền tảng Core Banking 2.0", "status": "ACTIVE", "department_id": 2},
    {"project_id": 2, "project_name": "Mobile App Khách hàng", "status": "ACTIVE", "department_id": 2},
    {"project_id": 3, "project_name": "AI Chatbot CSKH", "status": "ACTIVE", "department_id": 12},
    {"project_id": 4, "project_name": "Hệ thống CRM mới", "status": "ACTIVE", "department_id": 3},
]

# Edges: from -> to
MOCK_EDGES = [
    # ReportsTo
    (2, 1, "ReportsTo", "báo cáo cho"),
    (3, 1, "ReportsTo", "báo cáo cho"),
    (4, 1, "ReportsTo", "báo cáo cho"),
    (5, 1, "ReportsTo", "báo cáo cho"),
    (6, 3, "ReportsTo", "báo cáo cho"),
    (7, 3, "ReportsTo", "báo cáo cho"),
    (8, 6, "ReportsTo", "báo cáo cho"),
    (9, 8, "ReportsTo", "báo cáo cho"),
    (10, 7, "ReportsTo", "báo cáo cho"),
    (11, 9, "ReportsTo", "báo cáo cho"),
    (12, 10, "ReportsTo", "báo cáo cho"),
    (13, 6, "ReportsTo", "báo cáo cho"),
    (14, 8, "ReportsTo", "báo cáo cho"),
    (15, 8, "ReportsTo", "báo cáo cho"),
    (20, 11, "ReportsTo", "báo cáo cho"),
    (23, 4, "ReportsTo", "báo cáo cho"),
    (24, 23, "ReportsTo", "báo cáo cho"),
    (50, 2, "ReportsTo", "báo cáo cho"),
    (52, 50, "ReportsTo", "báo cáo cho"),
    (53, 52, "ReportsTo", "báo cáo cho"),
    (56, 2, "ReportsTo", "báo cáo cho"),
    (58, 56, "ReportsTo", "báo cáo cho"),
    (63, 3, "ReportsTo", "báo cáo cho"),
    (64, 63, "ReportsTo", "báo cáo cho"),
    # Knows
    (9, 8, "Knows", "MENTOR"),
    (11, 9, "Knows", "MENTOR"),
    (20, 11, "Knows", "MENTOR"),
    (8, 23, "Knows", "FRIEND"),
    (9, 24, "Knows", "COLLEAGUE"),
    (15, 64, "Knows", "COLLEAGUE"),
    (6, 63, "Knows", "FRIEND"),
    (3, 63, "Knows", "COLLEAGUE"),
    (52, 8, "Knows", "COLLEAGUE"),
    (53, 11, "Knows", "FRIEND"),
    (58, 12, "Knows", "COLLEAGUE"),
    # WorksOn
    (6, 8, "WorksOn", "đồng đội Core Banking"),
    (6, 9, "WorksOn", "đồng đội Core Banking"),
    (8, 9, "WorksOn", "đồng đội Core Banking"),
    (8, 11, "WorksOn", "đồng đội Core Banking"),
    (9, 11, "WorksOn", "đồng đội Core Banking"),
    (8, 13, "WorksOn", "đồng đội Core Banking"),
    (8, 15, "WorksOn", "đồng đội Core Banking"),
    (7, 10, "WorksOn", "đồng đội Mobile App"),
    (10, 12, "WorksOn", "đồng đội Mobile App"),
    (63, 64, "WorksOn", "đồng đội AI Chatbot"),
    (8, 64, "WorksOn", "đồng đội AI Chatbot"),
    (15, 64, "WorksOn", "đồng đội AI Chatbot"),
    (23, 24, "WorksOn", "đồng đội CRM"),
    (9, 23, "WorksOn", "đồng đội CRM"),
]

# Build adjacency (undirected for path finding)
_ADJ: dict[int, list[dict]] = {}
for e in MOCK_EMPLOYEES:
    _ADJ[e["employee_id"]] = []
for f, t, typ, lab in MOCK_EDGES:
    _ADJ.setdefault(f, []).append({"to": t, "type": typ, "label": lab})
    _ADJ.setdefault(t, []).append({"to": f, "type": typ, "label": lab})


import copy as _copy
_INITIAL_SNAPSHOT = {
    "employees": _copy.deepcopy(MOCK_EMPLOYEES),
    "departments": _copy.deepcopy(MOCK_DEPARTMENTS),
    "projects": _copy.deepcopy(MOCK_PROJECTS),
    "edges": _copy.deepcopy(MOCK_EDGES),
}
def _get_emp(eid: int) -> dict:
    for e in MOCK_EMPLOYEES:
        if e["employee_id"] == eid:
            return e
    return {"employee_id": eid, "full_name": "Unknown", "title": "", "department_name": "", "status": "INACTIVE"}


def mock_shortest_path(from_id: int, to_id: int, max_hops: int = 6) -> dict:
    if from_id == to_id:
        return {"found": False, "message": "Nguồn và đích trùng nhau"}
    src, dst = _get_emp(from_id), _get_emp(to_id)
    if src["full_name"] == "Unknown":
        return {"found": False, "message": "Nhân viên nguồn không tồn tại"}
    if dst["full_name"] == "Unknown":
        return {"found": False, "message": "Nhân viên đích không tồn tại"}

    queue: list[list[int]] = [[from_id]]
    visited = {from_id}
    while queue:
        path = queue.pop(0)
        cur = path[-1]
        if len(path) - 1 > max_hops:
            continue
        if cur == to_id:
            steps = []
            for i in range(len(path) - 1):
                a, b = path[i], path[i + 1]
                edge = next((x for x in _ADJ.get(a, []) if x["to"] == b), {"type": "Knows", "label": "kết nối"})
                ea, eb = _get_emp(a), _get_emp(b)
                steps.append({
                    "from_id": a, "from_name": ea["full_name"], "from_title": ea.get("title", ""),
                    "to_id": b, "to_name": eb["full_name"], "to_title": eb.get("title", ""),
                    "relation": edge["label"], "relation_type": edge["type"],
                })
            return {
                "found": True,
                "path_length": len(path) - 1,
                "nodes": [_get_emp(i) for i in path],
                "steps": steps,
                "from": src,
                "to": dst,
            }
        for nb in _ADJ.get(cur, []):
            if nb["to"] not in visited:
                visited.add(nb["to"])
                queue.append(path + [nb["to"]])
    return {"found": False, "message": f"Không tìm thấy đường kết nối trong {max_hops} bước", "from": src, "to": dst}


# ---------------------------------------------------------------------------
# Oracle connection (optional)
# ---------------------------------------------------------------------------
_pool = None
_oracledb = None


def _init_oracle() -> bool:
    global _pool, _oracledb
    if USE_MOCK:
        print("[Linko] USE_MOCK=true → chạy mock data")
        return False
    try:
        import oracledb as odb
        _oracledb = odb
        _pool = odb.create_pool(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_CONNECT,
            min=1,
            max=5,
            increment=1,
        )
        print(f"[Linko] Connected Oracle: {ORACLE_CONNECT}")
        return True
    except Exception as exc:
        print(f"[Linko] Oracle fail → fallback MOCK: {exc}")
        return False


def _oracle_query(sql: str, binds: dict | list | None = None) -> list[dict]:
    if not _pool:
        return []
    with _pool.acquire() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, binds or {})
            cols = [d[0].lower() for d in cur.description] if cur.description else []
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def _oracle_scalar(sql: str, binds: dict | None = None) -> Any:
    rows = _oracle_query(sql, binds)
    if not rows:
        return None
    return next(iter(rows[0].values()))


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ShortestPathRequest(BaseModel):
    from_id: int = Field(..., description="Employee ID nguồn")
    to_id: int = Field(..., description="Employee ID đích")
    max_hops: int = Field(6, ge=1, le=15, description="Số bước tối đa")


class CreateConnectionRequest(BaseModel):
    from_id: int
    to_id: int
    connection_type: str = "COLLEAGUE"
    strength: float = 1.0
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_oracle()
    from social_api import initialize_social_db
    initialize_social_db()
    yield
    if _pool:
        _pool.close()
        print("[Linko] Oracle _pool closed")



class CreateEmployee(BaseModel):
    full_name: str
    email: Optional[str] = None
    title: Optional[str] = "Nhân viên"
    department_id: int = 1
    department_name: Optional[str] = None
    status: str = "ACTIVE"


class UpdateEmployee(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    status: Optional[str] = None


app = FastAPI(
    title="Linko API",
    description=(
        "Hệ thống mạng xã hội nội bộ doanh nghiệp — Oracle 23ai SQL Property Graph.\n\n"
        "**Đề tài 17 · Nhóm 13 · HUFLIT**\n\n"
        "### Tính năng\n"
        "- CRUD nhân viên, phòng ban, dự án\n"
        "- Shortest path (BFS / PL/SQL GRAPH_TABLE)\n"
        "- Bạn chung, cây tổ chức, đồ thị overview\n"
        "- Sao lưu / khôi phục MOCK\n\n"
        "### Versioning\n"
        "- `/api/*` — ổn định (v1 tương thích)\n"
        "- `/api/v1/*` — alias cùng handler\n\n"
        "Header: `X-Request-ID`, `X-Process-Time`"
    ),
    version="6.0.0",
    lifespan=lifespan,
    contact={"name": "Nhóm 13"},
    license_info={"name": "Academic / HUFLIT 2026"},
    openapi_tags=[
        {"name": "System", "description": "Health, info, stats"},
        {"name": "Employees", "description": "CRUD & tìm kiếm nhân viên"},
        {"name": "Organization", "description": "Phòng ban, dự án, cây tổ chức"},
        {"name": "Graph", "description": "Property graph, path, connections"},
        {"name": "Data", "description": "Backup / restore / reset"},
        {"name": "Social", "description": "Bảng tin, bình luận, lượt thích, thông báo"},
    ],
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    # Cấu hình host frontend qua CORS_ORIGINS (phân tách bằng dấu phẩy).
    # Không dùng wildcard khi bật credentials để tránh cấu hình CORS không hợp lệ.
    allow_origins=[origin.strip() for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:4173"
    ).split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time", "X-API-Version"],
)


@app.middleware("http")
async def add_process_headers(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Request-ID"] = rid
    response.headers["X-Process-Time"] = f"{ms:.2f}ms"
    response.headers["X-API-Version"] = "6.0.0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def rewrite_v1_prefix(request: Request, call_next):
    """/api/v1/* → /api/* (versioning alias)."""
    path = request.scope.get("path", "")
    if path == "/api/v1" or path.startswith("/api/v1/"):
        new_path = "/api" + path[len("/api/v1"):]
        if new_path == "/api":
            new_path = "/api/info"
        request.scope["path"] = new_path
    return await call_next(request)


# Private workspace data must not be readable without authentication.
# Explicit public endpoints remain available for login, health and API documentation.
_PUBLIC_API_PATHS = {
    "/api/auth/login", "/api/health", "/api/info", "/api/auth/permissions"
}

@app.middleware("http")
async def protect_workspace_data(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/v1/"):
        path = "/api/" + path[len("/api/v1/"):]
    if request.method != "OPTIONS" and (path == "/api" or path.startswith("/api/")):
        if path not in _PUBLIC_API_PATHS and _user_from_request(request) is None:
            return JSONResponse(status_code=401, content={
                "ok": False, "error": "unauthorized", "detail": "Cần đăng nhập để xem dữ liệu nội bộ"
            })
    return await call_next(request)


# Serve static frontend if present
_STATIC = os.path.join(os.path.dirname(__file__), "..", "linko-static")
if os.path.isdir(_STATIC):
    app.mount("/static", StaticFiles(directory=_STATIC), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "ok": False,
            "error": "validation_error",
            "detail": [{key: value for key, value in issue.items() if key != "ctx"} for issue in exc.errors()],
            "path": str(request.url.path),
        },
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": "http_error",
            "detail": exc.detail,
            "status": exc.status_code,
            "path": str(request.url.path),
        },
    )



# ---------------------------------------------------------------------------
# Auth (demo roles)
# ---------------------------------------------------------------------------
_USERS = {
    "admin": {"password": "admin123", "full_name": "Quản trị hệ thống", "role": "admin"},
    "manager": {"password": "manager123", "full_name": "Trưởng phòng", "role": "manager"},
    "viewer": {"password": "viewer123", "full_name": "Nhân viên xem", "role": "viewer"},
}
_TOKENS: dict[str, tuple[str, float]] = {}  # token -> (username, monotonic expiry)
_LOGIN_FAILURES: dict[str, list[float]] = {}  # dev-mode brute-force throttle per client address
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 60


class LoginRequest(BaseModel):
    username: str
    password: str


def _user_from_request(request: Request) -> dict | None:
    auth = request.headers.get("Authorization") or ""
    token = ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    if not token:
        token = request.headers.get("X-Auth-Token") or ""
    if not token:
        return None
    session = _TOKENS.get(token)
    if not session:
        return None
    username, expires_at = session
    if time.monotonic() >= expires_at:
        _TOKENS.pop(token, None)
        return None
    u = _USERS.get(username)
    if not u:
        return None
    return {"username": username, "full_name": u["full_name"], "role": u["role"]}


# Ma trận quyền API (role -> allowed actions)
ROLE_PERMS: dict[str, set[str]] = {
    "admin": {
        "read", "path", "graph", "org", "audit",
        "employee_create", "employee_update", "employee_delete",
        "connection_create", "connection_delete",
        "org_create", "org_update", "org_delete",
        "backup", "restore", "reset", "export",
    },
    "manager": {
        "read", "path", "graph", "org", "audit",
        "employee_create", "employee_update",
        "connection_create", "org_create", "org_update",
        "backup", "export",
    },
    "viewer": {
        "read", "path", "graph", "org", "export",
    },
}


def _require_roles(request: Request, roles: list[str]):
    """Bắt buộc đăng nhập và role thuộc danh sách."""
    u = _user_from_request(request)
    if not u:
        raise HTTPException(401, "Chưa đăng nhập — POST /api/auth/login")
    if u["role"] not in roles:
        raise HTTPException(
            403,
            f"Role '{u['role']}' không được phép. Cần một trong: {', '.join(roles)}",
        )
    return u


def _require_perm(request: Request, perm: str):
    """Bắt buộc đăng nhập + quyền theo ROLE_PERMS."""
    u = _user_from_request(request)
    if not u:
        raise HTTPException(401, "Chưa đăng nhập — POST /api/auth/login")
    allowed = ROLE_PERMS.get(u["role"], set())
    if perm not in allowed:
        raise HTTPException(
            403,
            f"Role '{u['role']}' thiếu quyền '{perm}'",
        )
    return u


@app.post("/api/auth/login", tags=["System"])

def auth_login(body: LoginRequest, request: Request):
    client_key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = [t for t in _LOGIN_FAILURES.get(client_key, []) if now - t < LOGIN_WINDOW_SECONDS]
    if len(attempts) >= LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "Thử đăng nhập quá nhiều. Vui lòng chờ một phút.")
    u = _USERS.get(body.username)
    if not u or not hmac.compare_digest(u["password"].encode("utf-8"), body.password.encode("utf-8")):
        attempts.append(now)
        _LOGIN_FAILURES[client_key] = attempts
        raise HTTPException(401, "Sai tài khoản hoặc mật khẩu")
    _LOGIN_FAILURES.pop(client_key, None)
    import secrets
    token = secrets.token_urlsafe(32)
    now = time.monotonic()
    for old_token, (_, expires_at) in list(_TOKENS.items()):
        if expires_at <= now:
            _TOKENS.pop(old_token, None)
    _TOKENS[token] = (body.username, now + SESSION_TTL_SECONDS)
    return {
        "token": token,
        "username": body.username,
        "full_name": u["full_name"],
        "role": u["role"],
        "expires_in": SESSION_TTL_SECONDS,
    }


@app.get("/api/auth/me", tags=["System"])

def auth_me(request: Request):
    u = _user_from_request(request)
    if not u:
        raise HTTPException(401, "Chưa đăng nhập")
    return {
        "username": u["username"],
        "full_name": u["full_name"],
        "role": u["role"],
    }



@app.get("/api/auth/permissions", tags=["System"])

def auth_permissions(request: Request):
    """Ma trận quyền + user hiện tại (nếu có token)."""
    u = _user_from_request(request)
    return {
        "roles": {
            role: sorted(perms) for role, perms in ROLE_PERMS.items()
        },
        "matrix": {
            "employee_create": ["admin", "manager"],
            "employee_update": ["admin", "manager"],
            "employee_delete": ["admin"],
            "connection_create": ["admin", "manager"],
            "connection_delete": ["admin"],
            "org_create": ["admin", "manager"],
            "org_update": ["admin", "manager"],
            "org_delete": ["admin"],
            "backup": ["admin", "manager"],
            "restore": ["admin"],
            "reset": ["admin"],
            "audit": ["admin", "manager"],
            "read_all": ["admin", "manager", "viewer"],
        },
        "current": {
            "username": u["username"],
            "role": u["role"],
            "perms": sorted(ROLE_PERMS.get(u["role"], set())),
        }
        if u
        else None,
    }


@app.post("/api/auth/logout", tags=["System"])

def auth_logout(request: Request):
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        _TOKENS.pop(auth[7:].strip(), None)
    return {"ok": True}


@app.get("/api/health", tags=["System"])

def health():
    """Health check + mode."""
    return {
        "status": "ok",
        "mode": "oracle" if _pool else "mock",
        "version": "6.0.0",
        "framework": "FastAPI",
        "oracle_pool": bool(_pool),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/employees", tags=["Employees"])
def create_employee(body: CreateEmployee, request: Request):
    _require_perm(request, "employee_create")
    """Tạo nhân viên mới (MOCK: ghi vào list; Oracle: INSERT)."""
    name = (body.full_name or "").strip()
    if not name:
        raise HTTPException(400, "full_name bắt buộc")
    if USE_MOCK or not _pool:
        next_id = max((e["employee_id"] for e in MOCK_EMPLOYEES), default=0) + 1
        # resolve department name
        dept_name = body.department_name
        if not dept_name:
            for d in MOCK_DEPARTMENTS:
                if d.get("department_id") == body.department_id:
                    dept_name = d.get("department_name")
                    break
        emp = {
            "employee_id": next_id,
            "full_name": name,
            "email": body.email or f"user{next_id}@company.vn",
            "title": body.title or "Nhân viên",
            "department_id": body.department_id,
            "department_name": dept_name or "Khác",
            "status": body.status or "ACTIVE",
        }
        MOCK_EMPLOYEES.append(emp)
        return emp
    # Oracle path
    try:
        with _pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO employees (full_name, email, title, department_id, status)
                    VALUES (:n, :e, :t, :d, :s)
                    RETURNING employee_id INTO :id
                    """,
                    {
                        "n": name,
                        "e": body.email,
                        "t": body.title,
                        "d": body.department_id,
                        "s": body.status,
                        "id": cur.var(int),
                    },
                )
                # simpler fallback without RETURNING bind complexity
                conn.commit()
                cur.execute("SELECT MAX(employee_id) FROM employees")
                eid = cur.fetchone()[0]
                return {
                    "employee_id": eid,
                    "full_name": name,
                    "email": body.email,
                    "title": body.title,
                    "department_id": body.department_id,
                    "department_name": body.department_name,
                    "status": body.status,
                }
    except Exception as ex:
        raise HTTPException(500, f"Oracle insert failed: {ex}")



@app.put("/api/employees/{employee_id}", tags=["Employees"])
def update_employee(employee_id: int, body: UpdateEmployee, request: Request):
    _require_perm(request, "employee_update")
    """Sửa nhân viên (MOCK cập nhật list; Oracle UPDATE)."""
    if USE_MOCK or not _pool:
        for e in MOCK_EMPLOYEES:
            if e["employee_id"] == employee_id:
                data = body.model_dump(exclude_unset=True)
                if "full_name" in data and data["full_name"] is not None:
                    name = str(data["full_name"]).strip()
                    if not name:
                        raise HTTPException(400, "full_name không được rỗng")
                    e["full_name"] = name
                for k in ("email", "title", "status", "department_name"):
                    if k in data and data[k] is not None:
                        e[k] = data[k]
                if "department_id" in data and data["department_id"] is not None:
                    e["department_id"] = data["department_id"]
                    if not data.get("department_name"):
                        for d in MOCK_DEPARTMENTS:
                            if d.get("department_id") == data["department_id"]:
                                e["department_name"] = d.get("department_name")
                                break
                return e
        raise HTTPException(404, f"Employee {employee_id} not found")
    try:
        with _pool.acquire() as conn:
            with conn.cursor() as cur:
                fields = []
                binds = {"id": employee_id}
                data = body.model_dump(exclude_unset=True)
                mapping = {
                    "full_name": "full_name",
                    "email": "email",
                    "title": "title",
                    "department_id": "department_id",
                    "status": "status",
                }
                for k, col in mapping.items():
                    if k in data and data[k] is not None:
                        fields.append(f"{col} = :{k}")
                        binds[k] = data[k]
                if not fields:
                    raise HTTPException(400, "Không có trường để cập nhật")
                cur.execute(
                    f"UPDATE employees SET {', '.join(fields)} WHERE employee_id = :id",
                    binds,
                )
                if cur.rowcount == 0:
                    raise HTTPException(404, f"Employee {employee_id} not found")
                conn.commit()
                return get_employee(employee_id)
    except HTTPException:
        raise
    except Exception as ex:
        raise HTTPException(500, f"Oracle update failed: {ex}")


@app.delete("/api/employees/{employee_id}", tags=["Employees"])
def delete_employee(employee_id: int, request: Request):
    _require_perm(request, "employee_delete")
    """Xóa nhân viên (MOCK: remove list + edges; Oracle: DELETE)."""
    if USE_MOCK or not _pool:
        idx = next((i for i, e in enumerate(MOCK_EMPLOYEES) if e["employee_id"] == employee_id), None)
        if idx is None:
            raise HTTPException(404, f"Employee {employee_id} not found")
        removed = MOCK_EMPLOYEES.pop(idx)
        # clean edges
        global MOCK_EDGES, _ADJ
        MOCK_EDGES[:] = [e for e in MOCK_EDGES if e[0] != employee_id and e[1] != employee_id]
        _ADJ.pop(employee_id, None)
        for k in list(_ADJ.keys()):
            _ADJ[k] = [x for x in _ADJ[k] if x["to"] != employee_id]
        return {"ok": True, "deleted": removed}
    try:
        with _pool.acquire() as conn:
            with conn.cursor() as cur:
                # best-effort clean related edges if tables exist
                for sql in (
                    "DELETE FROM knows WHERE from_employee_id = :id OR to_employee_id = :id",
                    "DELETE FROM reports_to WHERE employee_id = :id OR manager_id = :id",
                    "DELETE FROM project_members WHERE employee_id = :id",
                    "DELETE FROM employees WHERE employee_id = :id",
                ):
                    try:
                        cur.execute(sql, {"id": employee_id})
                    except Exception:
                        pass
                conn.commit()
                return {"ok": True, "deleted_id": employee_id}
    except Exception as ex:
        raise HTTPException(500, f"Oracle delete failed: {ex}")


@app.get("/api/employees", tags=["Employees"])
def list_employees(q: Optional[str] = Query(None, description="Tìm theo tên / title / id")):
    if _pool:
        try:
            rows = _oracle_query(
                """
                SELECT e.employee_id, e.full_name, e.email, e.title,
                       e.department_id, e.status, d.department_name
                FROM employees e
                LEFT JOIN departments d ON e.department_id = d.department_id
                WHERE e.status = 'ACTIVE'
                ORDER BY e.full_name
                """
            )
            if rows:
                data = rows
            else:
                data = MOCK_EMPLOYEES
        except Exception:
            data = MOCK_EMPLOYEES
    else:
        data = MOCK_EMPLOYEES

    if q:
        ql = q.lower()
        data = [
            e for e in data
            if ql in (e.get("full_name") or "").lower()
            or ql in (e.get("title") or "").lower()
            or ql in str(e.get("employee_id", ""))
        ]
    return data


@app.get("/api/employees/{employee_id}", tags=["Employees"])
def get_employee(employee_id: int):
    if _pool:
        try:
            rows = _oracle_query(
                """
                SELECT e.*, d.department_name
                FROM employees e
                LEFT JOIN departments d ON e.department_id = d.department_id
                WHERE e.employee_id = :id
                """,
                {"id": employee_id},
            )
            if rows:
                return rows[0]
        except Exception:
            pass
    emp = _get_emp(employee_id)
    if emp["full_name"] == "Unknown":
        raise HTTPException(404, "Nhân viên không tồn tại")
    return emp


@app.get("/api/departments", tags=["Organization"])
def list_departments():
    if _pool:
        try:
            rows = _oracle_query("SELECT * FROM departments ORDER BY department_id")
            if rows:
                return rows
        except Exception:
            pass
    return MOCK_DEPARTMENTS


@app.get("/api/projects", tags=["Organization"])
def list_projects():
    if _pool:
        try:
            rows = _oracle_query("SELECT * FROM projects ORDER BY project_id")
            if rows:
                return rows
        except Exception:
            pass
    return MOCK_PROJECTS


@app.post("/api/paths/shortest", tags=["Graph"])
def shortest_path(body: ShortestPathRequest):
    """
    Tìm đường kết nối ngắn nhất giữa 2 nhân viên.
    - MOCK: BFS trong Python
    - Oracle: gọi pkg_social_network.find_shortest_path_length + GRAPH_TABLE (nếu có)
    """
    if _pool:
        try:
            # Gọi package PL/SQL
            length = _oracle_scalar(
                """
                SELECT pkg_social_network.find_shortest_path_length(
                    :from_id, :to_id, :max_hops
                ) AS path_len FROM dual
                """,
                {"from_id": body.from_id, "to_id": body.to_id, "max_hops": body.max_hops},
            )
            # Lấy chi tiết path bằng GRAPH_TABLE (nếu length không null)
            # Fallback: dùng mock BFS để có steps chi tiết
            result = mock_shortest_path(body.from_id, body.to_id, body.max_hops)
            if length is not None and result.get("found"):
                result["path_length"] = int(length) if length else result["path_length"]
                result["source"] = "oracle+mock_steps"
            return result
        except Exception as exc:
            # Fallback mock
            result = mock_shortest_path(body.from_id, body.to_id, body.max_hops)
            result["oracle_error"] = str(exc)
            return result

    return mock_shortest_path(body.from_id, body.to_id, body.max_hops)


@app.get("/api/employees/{employee_id}/connections", tags=["Graph"])
def connections(employee_id: int):
    """Kết nối trực tiếp (1 hop) — Knows | ReportsTo | WorksOn."""
    if _pool:
        try:
            rows = _oracle_query(
                """
                SELECT * FROM GRAPH_TABLE (
                  enterprise_social_graph
                  MATCH (
                    (me IS Employee WHERE me.employee_id = :id)
                    -[e IS Knows|ReportsTo]-{1,1}
                    (other IS Employee)
                  )
                  WHERE other.employee_id <> :id
                  COLUMNS (other.employee_id, other.full_name, other.title)
                )
                """,
                {"id": employee_id},
            )
            if rows:
                return rows
        except Exception:
            pass

    seen = set()
    result = []
    for nb in _ADJ.get(employee_id, []):
        if nb["to"] in seen:
            continue
        seen.add(nb["to"])
        emp = _get_emp(nb["to"])
        result.append({
            **emp,
            "relation": nb["label"],
            "relation_type": nb["type"],
        })
    return result


@app.get("/api/employees/{employee_id}/teammates", tags=["Graph"])
def teammates(employee_id: int):
    """Đồng đội cùng dự án."""
    if _pool:
        try:
            rows = _oracle_query(
                """
                SELECT DISTINCT t.employee_id, t.full_name, t.title,
                       p.project_name, pm.role
                FROM project_members me
                JOIN project_members pm ON me.project_id = pm.project_id
                JOIN employees t ON pm.employee_id = t.employee_id
                JOIN projects p ON me.project_id = p.project_id
                WHERE me.employee_id = :id
                  AND pm.employee_id <> :id
                  AND t.status = 'ACTIVE'
                ORDER BY p.project_name, t.full_name
                """,
                {"id": employee_id},
            )
            if rows is not None:
                return rows
        except Exception:
            pass

    return [
        {**_get_emp(nb["to"]), "relation": nb["label"]}
        for nb in _ADJ.get(employee_id, [])
        if nb["type"] == "WorksOn"
    ]


@app.get("/api/employees/{employee_id}/managers", tags=["Graph"])
def managers(employee_id: int):
    """Chuỗi quản lý lên cấp cao."""
    if _pool:
        try:
            rows = _oracle_query(
                """
                SELECT * FROM GRAPH_TABLE (
                  enterprise_social_graph
                  MATCH (
                    (me IS Employee WHERE me.employee_id = :id)
                    -[r IS ReportsTo]->{1,8}
                    (mgr IS Employee)
                  )
                  COLUMNS (mgr.employee_id, mgr.full_name, mgr.title, COUNT(r) AS level_num)
                )
                ORDER BY level_num
                """,
                {"id": employee_id},
            )
            if rows:
                return rows
        except Exception:
            pass

    chain = []
    cur = employee_id
    seen = set()
    while True:
        edge = next((e for e in MOCK_EDGES if e[0] == cur and e[2] == "ReportsTo"), None)
        if not edge or edge[1] in seen:
            break
        seen.add(edge[1])
        chain.append(_get_emp(edge[1]))
        cur = edge[1]
    return chain


@app.get("/api/employees/{employee_id}/stats", tags=["Graph"])
def network_stats(employee_id: int):
    if _pool:
        try:
            stats = _oracle_scalar(
                "SELECT pkg_social_network.get_network_stats(:id) FROM dual",
                {"id": employee_id},
            )
            if stats:
                return {"summary": stats, "source": "oracle"}
        except Exception:
            pass

    outgoing = sum(1 for e in MOCK_EDGES if e[0] == employee_id)
    incoming = sum(1 for e in MOCK_EDGES if e[1] == employee_id)
    projects = sum(1 for nb in _ADJ.get(employee_id, []) if nb["type"] == "WorksOn")
    return {
        "outgoing": outgoing,
        "incoming": incoming,
        "projects": projects,
        "total_connections": len(_ADJ.get(employee_id, [])),
        "summary": f"Outgoing: {outgoing} | Incoming: {incoming} | Projects: {projects}",
    }


@app.get("/api/graph/overview", tags=["Graph"])
def graph_overview(limit: int = Query(30, ge=5, le=100)):
    nodes = [
        {
            "id": e["employee_id"],
            "label": " ".join(e["full_name"].split()[-2:]),
            "title": f"{e['full_name']}\n{e.get('title','')}\n{e.get('department_name','')}",
            "group": e.get("department_id", 0),
        }
        for e in MOCK_EMPLOYEES[:limit]
    ]
    node_ids = {n["id"] for n in nodes}
    edges_out = []
    for i, (f, t, typ, lab) in enumerate(MOCK_EDGES):
        if f in node_ids and t in node_ids:
            edges_out.append({
                "id": i,
                "from": f,
                "to": t,
                "label": "QL" if typ == "ReportsTo" else ("DA" if typ == "WorksOn" else "KX"),
                "arrows": "to" if typ == "ReportsTo" else None,
                "color": "#e74c3c" if typ == "ReportsTo" else ("#3498db" if typ == "WorksOn" else "#95a5a6"),
            })
    return {"nodes": nodes, "edges": edges_out}


@app.post("/api/connections", tags=["Graph"])
def create_connection(body: CreateConnectionRequest, request: Request):
    """Tạo quan hệ Knows mới (gọi package nếu có Oracle)."""
    _require_perm(request, "connection_create")
    if _pool:
        try:
            with _pool.acquire() as conn:
                with conn.cursor() as cur:
                    cur.callproc(
                        "pkg_social_network.create_connection",
                        [body.from_id, body.to_id, body.connection_type, body.strength, body.notes],
                    )
                    conn.commit()
            return {"ok": True, "message": "Đã tạo quan hệ"}
        except Exception as exc:
            msg = str(exc)
            if "20001" in msg:
                raise HTTPException(400, "Không thể tạo quan hệ với chính mình")
            if "20002" in msg:
                raise HTTPException(404, "Nhân viên không tồn tại hoặc không active")
            if "20003" in msg:
                raise HTTPException(409, "Quan hệ đã tồn tại")
            raise HTTPException(500, f"Lỗi: {msg}")

    raise HTTPException(501, "Chế độ MOCK — không ghi được. Bật USE_MOCK=false và kết nối Oracle.")



@app.get("/api/employees/{employee_id}/common/{other_id}", tags=["Graph"])
def common_connections(employee_id: int, other_id: int):
    """Bạn chung / kết nối chung trong 1 hop (Knows|ReportsTo|WorksOn)."""
    if employee_id == other_id:
        return []
    # Mock: intersection of neighbors
    a = {nb["to"] for nb in _ADJ.get(employee_id, [])}
    b = {nb["to"] for nb in _ADJ.get(other_id, [])}
    common = a & b
    return [{**_get_emp(cid)} for cid in sorted(common)]


@app.get("/api/projects/{project_id}/members", tags=["Organization"])
def project_members(project_id: int):
    """Thành viên dự án (mock từ WorksOn edges + project_id loosely)."""
    # Return employees who appear on WorksOn edges as a stand-in
    members = []
    seen = set()
    for f, t, typ, lab in MOCK_EDGES:
        if typ != "WorksOn":
            continue
        if project_id == 1 and "Core" in lab:
            for eid in (f, t):
                if eid not in seen:
                    seen.add(eid)
                    members.append({**_get_emp(eid), "role": "MEMBER", "project_hint": lab})
        elif project_id == 2 and "Mobile" in lab:
            for eid in (f, t):
                if eid not in seen:
                    seen.add(eid)
                    members.append({**_get_emp(eid), "role": "MEMBER", "project_hint": lab})
        elif project_id == 3 and "AI" in lab:
            for eid in (f, t):
                if eid not in seen:
                    seen.add(eid)
                    members.append({**_get_emp(eid), "role": "MEMBER", "project_hint": lab})
        elif project_id == 4 and "CRM" in lab:
            for eid in (f, t):
                if eid not in seen:
                    seen.add(eid)
                    members.append({**_get_emp(eid), "role": "MEMBER", "project_hint": lab})
    return members



@app.get("/api/stats/overview", tags=["System"])
def stats_overview():
    """Thống kê tổng quan cho dashboard."""
    if USE_MOCK or not _pool:
        knows = sum(1 for e in MOCK_EDGES if e[2] == "Knows")
        reports = sum(1 for e in MOCK_EDGES if e[2] == "ReportsTo")
        works = sum(1 for e in MOCK_EDGES if e[2] == "WorksOn")
        return {
            "employees": len(MOCK_EMPLOYEES),
            "departments": len(MOCK_DEPARTMENTS),
            "projects": len(MOCK_PROJECTS),
            "edges_total": len(MOCK_EDGES),
            "edges_knows": knows,
            "edges_reports_to": reports,
            "edges_works_on": works,
            "mode": "mock",
        }
    try:
        with _pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM employees")
                n_emp = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM departments")
                n_dept = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM projects")
                n_proj = cur.fetchone()[0]
                counts = {}
                for table, key in (("knows", "knows"), ("reports_to", "reports_to"), ("project_members", "works_on")):
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        counts[key] = cur.fetchone()[0]
                    except Exception:
                        counts[key] = 0
                return {
                    "employees": n_emp,
                    "departments": n_dept,
                    "projects": n_proj,
                    "edges_total": sum(counts.values()),
                    "edges_knows": counts.get("knows", 0),
                    "edges_reports_to": counts.get("reports_to", 0),
                    "edges_works_on": counts.get("works_on", 0),
                    "mode": "oracle",
                }
    except Exception as ex:
        raise HTTPException(500, str(ex))



# ───────────────────────── Dashboard V2 ─────────────────────────

@app.get("/api/dashboard/overview", tags=["System"])
def dashboard_overview(request: Request):
    """Tổng quan dashboard lấy từ dữ liệu hiện tại, không tạo số liệu xu hướng giả.

    Trả về thống kê, phân bố theo phòng, dự án, và độ kết nối trong MOCK.
    Với Oracle chưa có truy vấn degree thống nhất, danh sách người có nhiều kết nối
    được để trống thay vì hiển thị dữ liệu MOCK như thể là dữ liệu thật.
    """
    _require_perm(request, "read")
    stats = stats_overview()
    employees = _all_employees()
    departments = _all_departments()
    projects = _all_projects()
    department_rows = []
    for department in departments:
        dept_id = department.get("department_id")
        department_rows.append({
            "department_id": dept_id,
            "name": department.get("department_name", "Chưa đặt tên"),
            "employee_count": sum(1 for employee in employees if employee.get("department_id") == dept_id),
            "project_count": sum(1 for project in projects if project.get("department_id") == dept_id),
        })
    department_rows.sort(key=lambda item: (-item["employee_count"], item["name"]))
    names = {d.get("department_id"): d.get("department_name") for d in departments}

    top_people = []
    if USE_MOCK or not _pool:
        scores: dict[int, int] = {}
        for source_id, target_id, _, _ in MOCK_EDGES:
            scores[source_id] = scores.get(source_id, 0) + 1
            scores[target_id] = scores.get(target_id, 0) + 1
        for employee in sorted(employees, key=lambda row: (-scores.get(row["employee_id"], 0), row["full_name"]))[:5]:
            top_people.append({
                "employee_id": employee["employee_id"],
                "name": employee["full_name"],
                "title": employee.get("title") or "Nhân viên",
                "department": employee.get("department_name") or names.get(employee.get("department_id"), "Khác"),
                "connections": scores.get(employee["employee_id"], 0),
            })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "departments": department_rows,
        "relationships": [
            {"key": "Knows", "name": "Quan hệ đồng nghiệp", "count": stats["edges_knows"]},
            {"key": "ReportsTo", "name": "Tuyến báo cáo", "count": stats["edges_reports_to"]},
            {"key": "WorksOn", "name": "Cùng dự án", "count": stats["edges_works_on"]},
        ],
        "top_people": top_people,
        "projects": [{
            "project_id": p.get("project_id"),
            "name": p.get("project_name", "Dự án"),
            "status": p.get("status", "UNKNOWN"),
            "department": names.get(p.get("department_id"), "Khác"),
        } for p in projects[:6]],
    }


# ───────────────────────── Organization (bổ sung) ─────────────────────────

class DepartmentIn(BaseModel):
    department_name: str = Field(min_length=2, max_length=120)
    location: Optional[str] = Field(None, max_length=200)

    @field_validator("department_name")
    @classmethod
    def validate_department_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Tên phòng ban phải có ít nhất 2 ký tự")
        return value


class ProjectIn(BaseModel):
    project_name: str = Field(min_length=2, max_length=120)
    status: str = Field("ACTIVE", pattern="^(ACTIVE|PAUSED|COMPLETED|CANCELLED)$")
    department_id: Optional[int] = Field(None, ge=1)

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Tên dự án phải có ít nhất 2 ký tự")
        return value


def _all_employees() -> list:
    if _pool:
        try:
            rows = _oracle_query(
                """
                SELECT e.employee_id, e.full_name, e.email, e.title,
                       e.department_id, e.status, d.department_name
                FROM employees e
                LEFT JOIN departments d ON e.department_id = d.department_id
                WHERE e.status = 'ACTIVE'
                ORDER BY e.full_name
                """
            )
            if rows:
                return rows
        except Exception:
            pass
    return MOCK_EMPLOYEES


def _all_departments() -> list:
    if _pool:
        try:
            rows = _oracle_query("SELECT * FROM departments ORDER BY department_id")
            if rows:
                return rows
        except Exception:
            pass
    return MOCK_DEPARTMENTS


def _all_projects() -> list:
    if _pool:
        try:
            rows = _oracle_query("SELECT * FROM projects ORDER BY project_id")
            if rows:
                return rows
        except Exception:
            pass
    return MOCK_PROJECTS


@app.get("/api/departments/stats", tags=["Organization"])
def departments_stats():
    """Số nhân viên + số dự án theo từng phòng ban."""
    emps = _all_employees()
    projs = _all_projects()
    out = []
    for d in _all_departments():
        did = d.get("department_id")
        out.append({
            **d,
            "employee_count": sum(1 for e in emps if e.get("department_id") == did),
            "project_count": sum(1 for p in projs if p.get("department_id") == did),
        })
    return out


@app.get("/api/departments/{department_id}", tags=["Organization"])
def get_department(department_id: int):
    for d in _all_departments():
        if d.get("department_id") == department_id:
            return d
    raise HTTPException(404, "Phòng ban không tồn tại")


@app.get("/api/departments/{department_id}/employees", tags=["Organization"])
def department_employees(department_id: int):
    get_department(department_id)
    return [e for e in _all_employees() if e.get("department_id") == department_id]


@app.get("/api/departments/{department_id}/projects", tags=["Organization"])
def department_projects(department_id: int):
    get_department(department_id)
    return [p for p in _all_projects() if p.get("department_id") == department_id]


def _ensure_mock_org_write():
    """Prevent false success: V5 organization CRUD only changes Python MOCK lists."""
    if _pool and not USE_MOCK:
        raise HTTPException(501, "CRUD phòng ban/dự án trong Oracle chưa triển khai. Không tự ghi dữ liệu MOCK.")


@app.post("/api/departments", tags=["Organization"], status_code=201)
def create_department(body: DepartmentIn, request: Request):
    _require_perm(request, "org_create")
    _ensure_mock_org_write()
    new_id = max([d["department_id"] for d in MOCK_DEPARTMENTS] or [0]) + 1
    row = {"department_id": new_id, "department_name": body.department_name, "location": body.location}
    MOCK_DEPARTMENTS.append(row)
    return row


@app.put("/api/departments/{department_id}", tags=["Organization"])
def update_department(department_id: int, body: DepartmentIn, request: Request):
    _require_perm(request, "org_update")
    _ensure_mock_org_write()
    for d in MOCK_DEPARTMENTS:
        if d["department_id"] == department_id:
            d["department_name"] = body.department_name
            d["location"] = body.location
            for e in MOCK_EMPLOYEES:
                if e.get("department_id") == department_id:
                    e["department_name"] = body.department_name
            return d
    raise HTTPException(404, "Phòng ban không tồn tại")


@app.delete("/api/departments/{department_id}", tags=["Organization"])
def delete_department(department_id: int, request: Request):
    _require_perm(request, "org_delete")
    _ensure_mock_org_write()
    if any(e.get("department_id") == department_id for e in MOCK_EMPLOYEES):
        raise HTTPException(409, "Phòng ban còn nhân viên, không thể xóa")
    if any(project.get("department_id") == department_id for project in MOCK_PROJECTS):
        raise HTTPException(409, "Phòng ban còn dự án, không thể xóa")
    for i, d in enumerate(MOCK_DEPARTMENTS):
        if d["department_id"] == department_id:
            MOCK_DEPARTMENTS.pop(i)
            return {"deleted": department_id}
    raise HTTPException(404, "Phòng ban không tồn tại")


@app.get("/api/projects/{project_id}", tags=["Organization"])
def get_project(project_id: int):
    for p in _all_projects():
        if p.get("project_id") == project_id:
            dept = next((d for d in _all_departments() if d.get("department_id") == p.get("department_id")), None)
            return {**p, "department_name": (dept or {}).get("department_name")}
    raise HTTPException(404, "Dự án không tồn tại")


@app.post("/api/projects", tags=["Organization"], status_code=201)
def create_project(body: ProjectIn, request: Request):
    _require_perm(request, "org_create")
    _ensure_mock_org_write()
    if body.department_id is not None and not any(d["department_id"] == body.department_id for d in MOCK_DEPARTMENTS):
        raise HTTPException(422, "Phòng ban của dự án không tồn tại")
    new_id = max([p["project_id"] for p in MOCK_PROJECTS] or [0]) + 1
    row = {"project_id": new_id, "project_name": body.project_name,
           "status": body.status, "department_id": body.department_id}
    MOCK_PROJECTS.append(row)
    return row


@app.put("/api/projects/{project_id}", tags=["Organization"])
def update_project(project_id: int, body: ProjectIn, request: Request):
    _require_perm(request, "org_update")
    _ensure_mock_org_write()
    if body.department_id is not None and not any(d["department_id"] == body.department_id for d in MOCK_DEPARTMENTS):
        raise HTTPException(422, "Phòng ban của dự án không tồn tại")
    for p in MOCK_PROJECTS:
        if p["project_id"] == project_id:
            p.update(project_name=body.project_name, status=body.status, department_id=body.department_id)
            return p
    raise HTTPException(404, "Dự án không tồn tại")


@app.delete("/api/projects/{project_id}", tags=["Organization"])
def delete_project(project_id: int, request: Request):
    _require_perm(request, "org_delete")
    _ensure_mock_org_write()
    for i, p in enumerate(MOCK_PROJECTS):
        if p["project_id"] == project_id:
            MOCK_PROJECTS.pop(i)
            return {"deleted": project_id}
    raise HTTPException(404, "Dự án không tồn tại")


@app.get("/api/org/summary", tags=["Organization"])
def org_summary():
    """Tổng quan tổ chức."""
    emps = _all_employees()
    return {
        "departments": len(_all_departments()),
        "projects": len(_all_projects()),
        "employees": len(emps),
        "active_projects": sum(1 for p in _all_projects() if p.get("status") == "ACTIVE"),
    }


@app.get("/api/org/tree", tags=["Organization"])
def org_tree(root_id: Optional[int] = Query(None)):
    """Cây tổ chức từ ReportsTo (MOCK BFS ngược từ edges)."""
    if True:  # Oracle: tạm dùng edges trong bộ nhớ làm fallback
        # build children map: manager -> [reports]
        children: dict = {}
        managers = set()
        reports = set()
        for f, t, typ, lab in MOCK_EDGES:
            if typ != "ReportsTo":
                continue
            # edge f->t : f reports to t? check label convention in mock
            # In our BFS edges: (from, to, type, label) for ReportsTo often subordinate->manager
            # Inspect: typically junior reports_to manager means edge junior -> manager
            children.setdefault(t, []).append(f)
            managers.add(t)
            reports.add(f)
        # roots = managers who are not reports, or CEO id 1
        roots = [r for r in managers if r not in reports] or [1]
        if root_id:
            roots = [root_id]

        def build(nid, depth=0, seen=None):
            if seen is None:
                seen = set()
            if nid in seen or depth > 8:
                return None
            seen.add(nid)
            emp = _get_emp(nid)
            kids = []
            for c in children.get(nid, []):
                node = build(c, depth + 1, seen)
                if node:
                    kids.append(node)
            return {
                **emp,
                "children": kids,
                "depth": depth,
            }

        trees = []
        for r in roots[:3]:
            node = build(r)
            if node:
                trees.append(node)
        return {"trees": trees, "mode": "mock" if (USE_MOCK or not _pool) else "oracle-fallback"}


@app.get("/api/audit/recent", tags=["System"])
def audit_recent(request: Request, limit: int = Query(20, ge=1, le=100)):
    """Log giả lập / audit_log nếu có."""
    _require_perm(request, "audit")
    if USE_MOCK or not _pool:
        # synthesize from edges
        rows = []
        for i, (f, t, typ, lab) in enumerate(reversed(MOCK_EDGES[-limit:])):
            rows.append({
                "id": i + 1,
                "action": f"EDGE_{typ}",
                "from_id": f,
                "to_id": t,
                "from_name": _get_emp(f).get("full_name"),
                "to_name": _get_emp(t).get("full_name"),
                "label": lab,
                "at": "2026-01-01T00:00:00",
            })
        return rows
    try:
        with _pool.acquire() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM (
                      SELECT audit_id, action, details, created_at
                      FROM audit_log ORDER BY created_at DESC
                    ) WHERE ROWNUM <= :lim
                    """,
                    {"lim": limit},
                )
                cols = [c[0].lower() for c in cur.description] if cur.description else []
                return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception:
        return []



@app.get("/api/data/backup", tags=["Data"])
def data_backup(request: Request):
    """Xuất toàn bộ dữ liệu MOCK (employees, departments, projects, edges)."""
    _require_perm(request, "backup")
    from datetime import datetime, timezone
    payload = {
        "version": 1,
        "app": "linko",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "mode": "mock" if (USE_MOCK or not _pool) else "oracle",
        "employees": list(MOCK_EMPLOYEES),
        "departments": list(MOCK_DEPARTMENTS),
        "projects": list(MOCK_PROJECTS),
        "edges": [
            {"from": f, "to": t, "type": typ, "label": lab}
            for f, t, typ, lab in MOCK_EDGES
        ],
    }
    if not USE_MOCK and _pool:
        # best-effort Oracle dump (read-only tables)
        try:
            payload["employees"] = _oracle_query(
                "SELECT e.employee_id, e.full_name, e.email, e.title, e.department_id, "
                "d.department_name, e.status FROM employees e "
                "LEFT JOIN departments d ON e.department_id = d.department_id ORDER BY e.employee_id"
            )
            payload["departments"] = _oracle_query("SELECT * FROM departments ORDER BY department_id")
            payload["projects"] = _oracle_query("SELECT * FROM projects ORDER BY project_id")
            payload["mode"] = "oracle"
        except Exception as ex:
            payload["oracle_warning"] = str(ex)
    return payload


class RestorePayload(BaseModel):
    employees: Optional[list] = None
    departments: Optional[list] = None
    projects: Optional[list] = None
    edges: Optional[list] = None
    version: Optional[int] = 1


@app.post("/api/data/restore", tags=["Data"])
def data_restore(body: RestorePayload, request: Request):
    _require_perm(request, "restore")
    """Khôi phục dữ liệu MOCK từ file backup JSON. (Oracle: chỉ hỗ trợ MOCK trong demo)."""
    if not USE_MOCK and _pool:
        raise HTTPException(
            501,
            "Khôi phục Oracle chưa hỗ trợ qua API demo — dùng SQL script. Bật USE_MOCK=true để restore.",
        )
    global MOCK_EMPLOYEES, MOCK_DEPARTMENTS, MOCK_PROJECTS, MOCK_EDGES, _ADJ

    if body.employees is not None:
        MOCK_EMPLOYEES[:] = [dict(e) for e in body.employees]
    if body.departments is not None:
        MOCK_DEPARTMENTS[:] = [dict(d) for d in body.departments]
    if body.projects is not None:
        MOCK_PROJECTS[:] = [dict(p) for p in body.projects]
    if body.edges is not None:
        new_edges = []
        for e in body.edges:
            if isinstance(e, (list, tuple)) and len(e) >= 4:
                new_edges.append((e[0], e[1], e[2], e[3]))
            elif isinstance(e, dict):
                new_edges.append(
                    (
                        int(e.get("from") or e.get("from_id")),
                        int(e.get("to") or e.get("to_id")),
                        str(e.get("type") or e.get("relation_type") or "Knows"),
                        str(e.get("label") or e.get("relation") or ""),
                    )
                )
        MOCK_EDGES[:] = new_edges

    # rebuild adjacency
    _ADJ.clear()
    for e in MOCK_EMPLOYEES:
        _ADJ.setdefault(e["employee_id"], [])
    for f, t, typ, lab in MOCK_EDGES:
        _ADJ.setdefault(f, []).append({"to": t, "type": typ, "label": lab})
        _ADJ.setdefault(t, []).append({"to": f, "type": typ, "label": lab})

    return {
        "ok": True,
        "employees": len(MOCK_EMPLOYEES),
        "departments": len(MOCK_DEPARTMENTS),
        "projects": len(MOCK_PROJECTS),
        "edges": len(MOCK_EDGES),
        "message": "Đã khôi phục dữ liệu MOCK",
    }


@app.post("/api/data/reset", tags=["Data"])
def data_reset(request: Request):
    _require_perm(request, "reset")
    """Khôi phục về snapshot ban đầu (nếu có), hoặc báo cần restart server."""
    if not USE_MOCK and _pool:
        raise HTTPException(501, "Reset chỉ dùng cho chế độ MOCK")
    snap = globals().get("_INITIAL_SNAPSHOT")
    if not snap:
        raise HTTPException(
            400,
            "Chưa có snapshot. Restart server rồi backup lần đầu sẽ tự tạo. Hoặc restore từ file.",
        )
    global MOCK_EMPLOYEES, MOCK_DEPARTMENTS, MOCK_PROJECTS, MOCK_EDGES, _ADJ
    import copy
    MOCK_EMPLOYEES[:] = copy.deepcopy(snap["employees"])
    MOCK_DEPARTMENTS[:] = copy.deepcopy(snap["departments"])
    MOCK_PROJECTS[:] = copy.deepcopy(snap["projects"])
    MOCK_EDGES[:] = copy.deepcopy(snap["edges"])
    _ADJ.clear()
    for e in MOCK_EMPLOYEES:
        _ADJ.setdefault(e["employee_id"], [])
    for f, t, typ, lab in MOCK_EDGES:
        _ADJ.setdefault(f, []).append({"to": t, "type": typ, "label": lab})
        _ADJ.setdefault(t, []).append({"to": f, "type": typ, "label": lab})
    return {
        "ok": True,
        "employees": len(MOCK_EMPLOYEES),
        "edges": len(MOCK_EDGES),
        "message": "Đã reset về snapshot khởi động",
    }




# ---------------------------------------------------------------------------
# API v2 enhancements
# ---------------------------------------------------------------------------
@app.get("/api/info", tags=["System"])

def api_info():
    """Thông tin API, mode, số liệu nhanh."""
    return {
        "name": "Linko API",
        "version": "6.0.0",
        "mode": "oracle" if _pool else "mock",
        "use_mock_flag": USE_MOCK,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "employees": len(MOCK_EMPLOYEES),
            "departments": len(MOCK_DEPARTMENTS),
            "projects": len(MOCK_PROJECTS),
            "edges": len(MOCK_EDGES),
        },
        "endpoints": {
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/api/health",
            "v1_prefix": "/api/v1",
        },
        "features": [
            "shortest_path",
            "common_connections",
            "org_tree",
            "crud_employees",
            "backup_restore",
            "graph_overview",
            "subordinates",
            "batch_employees",
            "paginated_search", "k_shortest", "neighborhood", "centrality", "components", "diameter", "csv_export", "bulk_delete", "path_filter",
        ],
    }


@app.get("/api/search/employees", tags=["Employees"])

def search_employees(
    q: Optional[str] = Query(None, description="Từ khóa tên/email/title/id"),
    department_id: Optional[int] = Query(None),
    title: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("name", description="name|id|title"),
):
    """Tìm kiếm nhân viên có phân trang."""
    data = list(MOCK_EMPLOYEES)
    if _pool and not USE_MOCK:
        try:
            data = _oracle_query(
                "SELECT e.employee_id, e.full_name, e.email, e.title, e.department_id, "
                "d.department_name, e.status FROM employees e "
                "LEFT JOIN departments d ON e.department_id = d.department_id"
            )
        except Exception:
            pass
    if q:
        qq = q.lower().strip()
        tokens = qq.split()
        def match(e):
            hay = " ".join([
                str(e.get("full_name") or ""),
                str(e.get("email") or ""),
                str(e.get("title") or ""),
                str(e.get("department_name") or ""),
                str(e.get("employee_id") or ""),
            ]).lower()
            return all(tok in hay for tok in tokens)
        data = [e for e in data if match(e)]
    if department_id is not None:
        data = [e for e in data if e.get("department_id") == department_id]
    if title:
        tl = title.lower()
        data = [e for e in data if tl in (e.get("title") or "").lower()]
    if status:
        data = [e for e in data if (e.get("status") or "").upper() == status.upper()]
    if sort not in ("name", "id", "title"):
        sort = "name"
    if sort == "id":
        data.sort(key=lambda e: e.get("employee_id") or 0)
    elif sort == "title":
        data.sort(key=lambda e: (e.get("title") or ""))
    else:
        data.sort(key=lambda e: (e.get("full_name") or ""))
    total = len(data)
    start = (page - 1) * page_size
    items = data[start : start + page_size]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }


@app.get("/api/employees/{employee_id}/subordinates", tags=["Graph"])

def subordinates(employee_id: int, max_depth: int = Query(3, ge=1, le=8)):
    """Cấp dưới theo ReportsTo (BFS từ manager)."""
    # edge: subordinate -> manager (ReportsTo)
    children: dict[int, list[int]] = {}
    for f, t, typ, lab in MOCK_EDGES:
        if typ != "ReportsTo":
            continue
        children.setdefault(t, []).append(f)
    result = []
    queue = [(employee_id, 0)]
    seen = {employee_id}
    while queue:
        nid, depth = queue.pop(0)
        if depth >= max_depth:
            continue
        for c in children.get(nid, []):
            if c in seen:
                continue
            seen.add(c)
            emp = _get_emp(c)
            result.append({**emp, "depth": depth + 1, "manager_id": nid})
            queue.append((c, depth + 1))
    return {"manager_id": employee_id, "count": len(result), "subordinates": result}


@app.post("/api/employees/batch", tags=["Employees"])

def batch_create_employees(body: list[CreateEmployee], request: Request):
    """Tạo nhiều nhân viên (MOCK). Tối đa 50."""
    _require_perm(request, "employee_create")
    if len(body) > 50:
        raise HTTPException(400, "Tối đa 50 nhân viên mỗi lần")
    created = []
    for item in body:
        created.append(create_employee(item, request))
    return {"ok": True, "count": len(created), "employees": created}


@app.get("/api/paths/exists", tags=["Graph"])

def path_exists(
    from_id: int = Query(...),
    to_id: int = Query(...),
    max_hops: int = Query(6, ge=1, le=15),
):
    """Kiểm tra nhanh có đường nối không (không trả chi tiết bước)."""
    r = mock_shortest_path(from_id, to_id, max_hops)
    return {
        "from_id": from_id,
        "to_id": to_id,
        "exists": bool(r.get("found")),
        "path_length": r.get("path_length"),
        "message": r.get("message"),
    }


@app.get("/api/graph/edges", tags=["Graph"])

def list_edges(
    type: Optional[str] = Query(None, description="Knows|ReportsTo|WorksOn"),
    limit: int = Query(100, ge=1, le=500),
):
    """Liệt kê cạnh graph."""
    rows = []
    for f, t, typ, lab in MOCK_EDGES:
        if type and typ.lower() != type.lower():
            continue
        rows.append({
            "from_id": f,
            "to_id": t,
            "type": typ,
            "label": lab,
            "from_name": _get_emp(f).get("full_name"),
            "to_name": _get_emp(t).get("full_name"),
        })
        if len(rows) >= limit:
            break
    return {"count": len(rows), "edges": rows}


@app.get("/api/graph/degree/{employee_id}", tags=["Graph"])

def node_degree(employee_id: int):
    """Bậc đỉnh (số cạnh) của nhân viên."""
    out_n = sum(1 for e in MOCK_EDGES if e[0] == employee_id)
    in_n = sum(1 for e in MOCK_EDGES if e[1] == employee_id)
    by_type: dict[str, int] = {}
    for f, t, typ, lab in MOCK_EDGES:
        if f == employee_id or t == employee_id:
            by_type[typ] = by_type.get(typ, 0) + 1
    return {
        "employee_id": employee_id,
        "employee": _get_emp(employee_id),
        "out_degree": out_n,
        "in_degree": in_n,
        "total_touching": by_type and sum(by_type.values()) or 0,
        "by_type": by_type,
    }



# ===========================================================================
# API v3 — maximum graph & data capabilities
# ===========================================================================

class PathFilterRequest(BaseModel):
    from_id: int
    to_id: int
    max_hops: int = Field(6, ge=1, le=15)
    edge_types: Optional[list[str]] = Field(
        None, description="Lọc loại cạnh: Knows, ReportsTo, WorksOn"
    )


class BulkDeleteRequest(BaseModel):
    employee_ids: list[int] = Field(..., min_length=1, max_length=50)


class CompareRequest(BaseModel):
    a_id: int
    b_id: int


def _rebuild_adj():
    _ADJ.clear()
    for e in MOCK_EMPLOYEES:
        _ADJ.setdefault(e["employee_id"], [])
    for f, t, typ, lab in MOCK_EDGES:
        _ADJ.setdefault(f, []).append({"to": t, "type": typ, "label": lab})
        _ADJ.setdefault(t, []).append({"to": f, "type": typ, "label": lab})


def _shortest_filtered(from_id: int, to_id: int, max_hops: int, edge_types: Optional[list[str]]):
    allowed = {x.lower() for x in edge_types} if edge_types else None
    if from_id == to_id:
        return {"found": False, "message": "Nguồn và đích trùng nhau"}
    from collections import deque
    q = deque([(from_id, [from_id], [])])
    seen = {from_id}
    while q:
        cur, path, steps = q.popleft()
        if len(path) - 1 >= max_hops:
            continue
        for nb in _ADJ.get(cur, []):
            if allowed and nb["type"].lower() not in allowed:
                continue
            nxt = nb["to"]
            if nxt in seen:
                continue
            npath = path + [nxt]
            nsteps = steps + [{
                "from_id": cur,
                "from_name": _get_emp(cur).get("full_name"),
                "to_id": nxt,
                "to_name": _get_emp(nxt).get("full_name"),
                "relation": nb.get("label") or nb["type"],
                "relation_type": nb["type"],
            }]
            if nxt == to_id:
                return {
                    "found": True,
                    "path_length": len(npath) - 1,
                    "nodes": [_get_emp(i) for i in npath],
                    "steps": nsteps,
                    "from": _get_emp(from_id),
                    "to": _get_emp(to_id),
                    "edge_types_filter": edge_types,
                }
            seen.add(nxt)
            q.append((nxt, npath, nsteps))
    return {"found": False, "message": "Không tìm thấy đường trong giới hạn hops/filter"}


@app.post("/api/paths/shortest/filtered", tags=["Graph"])

def shortest_path_filtered(body: PathFilterRequest):
    """Shortest path chỉ đi qua các loại cạnh chỉ định."""
    return _shortest_filtered(body.from_id, body.to_id, body.max_hops, body.edge_types)


@app.get("/api/paths/k-shortest", tags=["Graph"])

def k_shortest(
    from_id: int = Query(...),
    to_id: int = Query(...),
    k: int = Query(3, ge=1, le=10),
    max_hops: int = Query(8, ge=1, le=15),
):
    """K đường ngắn nhất (Yen-lite: BFS enumeration, unique path sets)."""
    from collections import deque
    found = []
    q = deque([(from_id, [from_id], [])])
    while q and len(found) < k:
        cur, path, steps = q.popleft()
        if len(path) - 1 > max_hops:
            continue
        if cur == to_id and len(path) > 1:
            key = tuple(path)
            if not any(tuple(x["node_ids"]) == key for x in found):
                found.append({
                    "path_length": len(path) - 1,
                    "node_ids": path,
                    "nodes": [_get_emp(i) for i in path],
                    "steps": steps,
                })
            continue
        for nb in _ADJ.get(cur, []):
            nxt = nb["to"]
            if nxt in path:
                continue
            q.append((
                nxt,
                path + [nxt],
                steps + [{
                    "from_id": cur,
                    "to_id": nxt,
                    "relation": nb.get("label") or nb["type"],
                    "relation_type": nb["type"],
                }],
            ))
    return {
        "from_id": from_id,
        "to_id": to_id,
        "k": k,
        "found": len(found),
        "paths": found,
    }


@app.get("/api/graph/neighborhood/{employee_id}", tags=["Graph"])

def neighborhood(
    employee_id: int,
    depth: int = Query(1, ge=1, le=4),
    edge_types: Optional[str] = Query(None, description="Comma: Knows,ReportsTo,WorksOn"),
):
    """Ego-network: đỉnh + cạnh trong bán kính depth."""
    allowed = {x.strip().lower() for x in edge_types.split(",")} if edge_types else None
    nodes = {employee_id}
    frontier = {employee_id}
    edge_set = []
    for d in range(depth):
        nxt_front = set()
        for u in frontier:
            for nb in _ADJ.get(u, []):
                if allowed and nb["type"].lower() not in allowed:
                    continue
                v = nb["to"]
                edge_set.append((min(u, v), max(u, v), nb["type"], nb.get("label") or ""))
                if v not in nodes:
                    nodes.add(v)
                    nxt_front.add(v)
        frontier = nxt_front
    # unique edges
    seen_e = set()
    edges = []
    for a, b, typ, lab in edge_set:
        key = (a, b, typ)
        if key in seen_e:
            continue
        seen_e.add(key)
        edges.append({
            "from": a, "to": b, "type": typ, "label": lab,
            "from_name": _get_emp(a).get("full_name"),
            "to_name": _get_emp(b).get("full_name"),
        })
    return {
        "center_id": employee_id,
        "depth": depth,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": [_get_emp(i) for i in sorted(nodes)],
        "edges": edges,
    }


@app.get("/api/graph/centrality", tags=["Graph"])

def centrality(limit: int = Query(15, ge=1, le=50)):
    """Xếp hạng degree centrality (xấp xỉ tầm ảnh hưởng trong mạng)."""
    scores: dict[int, int] = {}
    for f, t, typ, lab in MOCK_EDGES:
        scores[f] = scores.get(f, 0) + 1
        scores[t] = scores.get(t, 0) + 1
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:limit]
    return {
        "metric": "degree_centrality",
        "ranking": [
            {
                **_get_emp(eid),
                "degree": deg,
                "rank": i + 1,
            }
            for i, (eid, deg) in enumerate(ranked)
        ],
    }


@app.get("/api/graph/components", tags=["Graph"])

def connected_components():
    """Thành phần liên thông (undirected)."""
    ids = [e["employee_id"] for e in MOCK_EMPLOYEES]
    seen = set()
    comps = []
    for start in ids:
        if start in seen:
            continue
        stack = [start]
        comp = []
        seen.add(start)
        while stack:
            u = stack.pop()
            comp.append(u)
            for nb in _ADJ.get(u, []):
                v = nb["to"]
                if v not in seen and any(x["employee_id"] == v for x in MOCK_EMPLOYEES):
                    seen.add(v)
                    stack.append(v)
        comps.append(sorted(comp))
    comps.sort(key=len, reverse=True)
    return {
        "component_count": len(comps),
        "largest": len(comps[0]) if comps else 0,
        "components": [
            {"size": len(c), "member_ids": c, "members": [_get_emp(i).get("full_name") for i in c[:12]]}
            for c in comps
        ],
    }


@app.get("/api/graph/diameter", tags=["Graph"])

def graph_diameter(sample: int = Query(12, ge=3, le=40)):
    """Ước lượng đường kính (max shortest-path) trên mẫu đỉnh."""
    ids = [e["employee_id"] for e in MOCK_EMPLOYEES][:sample]
    max_d = 0
    pair = None
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            r = mock_shortest_path(a, b, max_hops=12)
            if r.get("found"):
                d = r["path_length"]
                if d > max_d:
                    max_d = d
                    pair = (a, b)
    return {
        "sample_size": len(ids),
        "estimated_diameter": max_d,
        "pair": {
            "from_id": pair[0] if pair else None,
            "to_id": pair[1] if pair else None,
            "from_name": _get_emp(pair[0]).get("full_name") if pair else None,
            "to_name": _get_emp(pair[1]).get("full_name") if pair else None,
        }
        if pair
        else None,
    }


@app.post("/api/employees/compare", tags=["Employees"])

def compare_employees(body: CompareRequest):
    """So sánh 2 NV: managers, teammates, common, path."""
    a, b = body.a_id, body.b_id
    path = mock_shortest_path(a, b, 8)
    common = common_connections(a, b)
    return {
        "a": _get_emp(a),
        "b": _get_emp(b),
        "path": path,
        "common_connections": common,
        "stats_a": network_stats(a),
        "stats_b": network_stats(b),
    }


@app.delete("/api/employees/batch", tags=["Employees"])

def bulk_delete_employees(body: BulkDeleteRequest, request: Request):
    """Xóa hàng loạt (MOCK)."""
    _require_perm(request, "employee_delete")
    if not USE_MOCK and _pool:
        raise HTTPException(501, "Bulk delete Oracle chưa hỗ trợ trong demo")
    deleted = []
    for eid in body.employee_ids:
        try:
            r = delete_employee(eid, request)
            deleted.append(eid)
        except HTTPException:
            pass
    return {"ok": True, "deleted_ids": deleted, "count": len(deleted)}


@app.get("/api/connections", tags=["Graph"])

def list_all_connections(
    type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
):
    """Danh sách cạnh có phân trang."""
    rows = []
    for f, t, typ, lab in MOCK_EDGES:
        if type and typ.lower() != type.lower():
            continue
        rows.append({
            "from_id": f,
            "to_id": t,
            "type": typ,
            "label": lab,
            "from_name": _get_emp(f).get("full_name"),
            "to_name": _get_emp(t).get("full_name"),
        })
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": rows[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }


@app.delete("/api/connections", tags=["Graph"])

def delete_connection(
    request: Request,
    from_id: int = Query(...),
    to_id: int = Query(...),
    type: Optional[str] = Query(None),
):
    """Xóa cạnh MOCK giữa 2 NV."""
    _require_perm(request, "connection_delete")
    if not USE_MOCK and _pool:
        raise HTTPException(501, "Chỉ MOCK")
    global MOCK_EDGES
    before = len(MOCK_EDGES)
    MOCK_EDGES[:] = [
        e
        for e in MOCK_EDGES
        if not (
            ((e[0] == from_id and e[1] == to_id) or (e[0] == to_id and e[1] == from_id))
            and (type is None or e[2].lower() == type.lower())
        )
    ]
    _rebuild_adj()
    return {"ok": True, "removed": before - len(MOCK_EDGES)}


@app.get("/api/export/employees.csv", tags=["Data"])

def export_employees_csv(request: Request):
    """Xuất CSV nhân viên."""
    _require_perm(request, "export")
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["employee_id", "full_name", "email", "title", "department_id", "department_name", "status"])
    for e in MOCK_EMPLOYEES:
        w.writerow([
            e.get("employee_id"), e.get("full_name"), e.get("email"), e.get("title"),
            e.get("department_id"), e.get("department_name"), e.get("status"),
        ])
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@app.get("/api/export/edges.csv", tags=["Data"])

def export_edges_csv(request: Request):
    """Xuất CSV cạnh graph."""
    _require_perm(request, "export")
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["from_id", "to_id", "type", "label"])
    for f, t, typ, lab in MOCK_EDGES:
        w.writerow([f, t, typ, lab])
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=edges.csv"},
    )


@app.get("/api/metrics", tags=["System"])

def metrics():
    """Metrics nội bộ (JSON, không Prometheus)."""
    return {
        "version": "6.0.0",
        "mode": "oracle" if _pool else "mock",
        "employees": len(MOCK_EMPLOYEES),
        "departments": len(MOCK_DEPARTMENTS),
        "projects": len(MOCK_PROJECTS),
        "edges": len(MOCK_EDGES),
        "edges_by_type": {
            "Knows": sum(1 for e in MOCK_EDGES if e[2] == "Knows"),
            "ReportsTo": sum(1 for e in MOCK_EDGES if e[2] == "ReportsTo"),
            "WorksOn": sum(1 for e in MOCK_EDGES if e[2] == "WorksOn"),
        },
        "adj_nodes": len(_ADJ),
    }


@app.get("/api/openapi/summary", tags=["System"])

def openapi_summary():
    """Tóm tắt routes đang đăng ký."""
    routes = []
    for r in app.routes:
        methods = getattr(r, "methods", None)
        path = getattr(r, "path", None)
        if path and methods:
            routes.append({"path": path, "methods": sorted(m for m in methods if m != "HEAD")})
    routes.sort(key=lambda x: x["path"])
    return {"version": "6.0.0", "route_count": len(routes), "routes": routes}



@app.get("/", tags=["System"])

def root():
    """Landing — chuyển docs."""
    return {
        "message": "Linko API v5.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
        "info": "/api/info",
        "v1_alias": "/api/v1/* → /api/*",
    }


# ---------------------------------------------------------------------------
# Social feed uses a separate persistent SQLite store and demo session tokens.
# ---------------------------------------------------------------------------
from social_api import mount_social_routes

def _require_social_user(request: Request) -> dict:
    user = _user_from_request(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập")
    return user

mount_social_routes(app, _require_social_user, _USERS)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
