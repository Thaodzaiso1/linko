"""FastAPI REST entry point for enterprise_social_graph on Oracle Database 23ai.

Run from this folder:
    uvicorn main:app --reload --host 127.0.0.1 --port 8000

This demonstration backend intentionally allows all CORS origins, as specified.
For Internet exposure, configure authentication/authorization, rate limiting,
TLS termination, and restricted origins at the deployment gateway.
"""

from __future__ import annotations

import logging
import os
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from security import validate_token, required_role, allowed_role, AuthError, auth_failure, current_actor
from typing import Any, Callable, Literal, TypeVar

import oracledb
from fastapi import FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

from database import close_pool, get_connection, initialize_pool, scalar
from exceptions import handle_oracle_error, api_error
from graph_service import (
    add_project_member, audit_logs, check_teammate, connection_create,
    connection_delete, connection_update, demo_presets, department_list,
    employee_profile, find_employees, khops_graph, project_list, shortest_path,
    stats, subordinates, teammates_graph,
)
from extended import make_router
from crud_v6 import make_router as make_data_router
from v7_core_compat import make_compat_router
from schemas import (
    ComparisonResponse, ConnectionCreate, ConnectionDelete, ConnectionUpdate,
    EmployeeProfileResponse, EmployeeSummary, GraphResponse, HealthResponse,
    MutationResponse, ProjectMemberCreate, ProjectMemberResponse,
    ShortestPathRequest, ShortestPathResponse, StatsResponse,
    DepartmentResponse, ProjectResponse, TeammateCheckResponse,
    AuditLogResponse, DemoPresetResponse,
)

logging.basicConfig(level=os.getenv("APP_LOG_LEVEL", "INFO").upper())
logger = logging.getLogger("enterprise_social_api")
T = TypeVar("T")


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Never fall back to fake data when Oracle is unavailable. Exposing /docs
    # and /api/live still works, but DB endpoints return HTTP 503.
    try:
        initialize_pool()
    except (RuntimeError, ValueError, oracledb.Error) as exc:
        logger.warning("Oracle not ready: %s", exc)
    try:
        yield
    finally:
        close_pool()


app = FastAPI(
    title="Linko Enterprise Social Network – Oracle 23ai",
    description=("Đề tài 17 – Nhóm 13. REST API kết nối Property Graph, "
                 "PL/SQL packages, triggers và dữ liệu nhân sự."),
    version="7.0.0",
    lifespan=lifespan,
)

# Restrict CORS by default. Same-origin SPA access needs no CORS header.
# To allow Vite/dev UI, list origins in CORS_ORIGINS separated by commas.
_cors_origins = [x.strip() for x in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
).split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID", "If-Match"],
)

@app.middleware("http")
async def request_guard_and_id(request: Request, call_next):
    request_id = uuid4().hex
    started = time.perf_counter()
    # Public process liveness (not database readiness); health/ready require role.
    # Browser preflights contain no Authorization header and do not touch Oracle.
    ctx = None
    if request.url.path.startswith('/api/') and request.url.path != '/api/live' and request.method != 'OPTIONS':
        try:
            principal = validate_token(request.headers.get('Authorization', ''))
            needed = required_role(request)
            if not allowed_role(principal.role, needed):
                raise AuthError('FORBIDDEN', f'Cần vai trò {needed} trở lên.', 403)
            # Risky hard deletions are always restricted to admin by DELETE policy.
            ctx = current_actor.set(principal.subject)
            request.state.principal = principal
        except AuthError as err:
            return auth_failure(err, request_id)
    try:
        response = await call_next(request)
    finally:
        if ctx is not None:
            current_actor.reset(ctx)
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith('/api/') else "no-cache"
    logger.info("%s %s -> %s (%.1fms) request_id=%s", request.method,
                request.url.path, response.status_code,
                (time.perf_counter() - started)*1000, request_id)
    return response


def db_action(operation: Callable[[oracledb.Connection], T], write: bool = False) -> T:
    """One transaction per API request: commit on success, rollback otherwise.

    PL/SQL packages called by write endpoints must not COMMIT internally.
    """
    try:
        with get_connection() as connection:
            try:
                # Oracle trigger audit reads SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER').
                # Always clear the pooled session to avoid identity leakage.
                actor = current_actor.get()
                connection.client_identifier = actor if actor != 'ANONYMOUS' else None
                result = operation(connection)
                if write:
                    connection.commit()
                else:
                    # A read must never leak session transaction state into pool.
                    connection.rollback()
                return result
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.client_identifier = None
    except HTTPException:
        raise
    except oracledb.Error as error:
        handle_oracle_error(error)
        raise AssertionError("handle_oracle_error must raise")
    except (RuntimeError, ValueError, OSError) as error:
        logger.error("Oracle is not available: %s", error)
        raise api_error(503, "DATABASE_UNAVAILABLE", "Oracle 23ai chưa sẵn sàng. Kiểm tra .env và kết nối DB.") from error


@app.get("/api/live", tags=["System"])
def live() -> dict[str, str]:
    """Process liveness only; /api/health checks a real Oracle connection."""
    return {"status": "running", "database": "not_checked", "mode": "oracle_only"}


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
def health() -> dict[str, Any]:
    def operation(connection: oracledb.Connection):
        value = scalar(connection, "SELECT SYS_CONTEXT('USERENV','DB_NAME') FROM dual")
        return {"status": "ok", "database": str(value), "thin_mode": oracledb.is_thin_mode()}
    return db_action(operation)


@app.get("/api/ready", tags=["System"])
def ready() -> dict[str, Any]:
    """Database readiness with actual schema/graph query, not dummy success."""
    def operation(connection: oracledb.Connection):
        needed = ("EMPLOYEES", "DEPARTMENTS", "PROJECTS", "REPORTS_TO",
                  "PROJECT_MEMBERS", "KNOWS", "AUDIT_LOG", "PKG_SOCIAL_NETWORK",
                  "TRG_AUTO_TEAMMATE", "TRG_AUDIT_KNOWS",
                  "TRG_AUDIT_EMPLOYEES", "TRG_AUDIT_DEPARTMENTS", "TRG_AUDIT_PROJECTS",
                  "TRG_AUDIT_PROJECT_MEMBERS", "TRG_AUDIT_REPORTS_TO")
        from database import query_all
        objects = query_all(connection, """SELECT object_name, object_type, status FROM user_objects
             WHERE object_name IN (""" + ",".join(":" + f"obj{i}" for i in range(len(needed))) + ")",
             {f"obj{i}": name for i, name in enumerate(needed)})
        present = {item["object_name"] for item in objects if item["status"] == "VALID"}
        missing = sorted(set(needed) - present)
        if missing:
            raise api_error(503, "SCHEMA_NOT_READY", "Thiếu/invalid Oracle objects: " + ", ".join(missing))
        # Requires actual property graph to exist and GRAPH_TABLE to compile.
        scalar(connection, """SELECT COUNT(*) FROM GRAPH_TABLE (
            enterprise_social_graph MATCH (a IS Employee)
            WHERE a.employee_id = -987654321
            COLUMNS (a.employee_id AS employee_id))""")
        return {"status": "ready", "mode": "oracle23ai", "schema_objects_valid": len(needed),
                "property_graph": "enterprise_social_graph"}
    return db_action(operation)


@app.get("/api/employees", response_model=list[EmployeeSummary], tags=["Directory"])
def get_employees(
    q: str | None = Query(default=None, max_length=150),
    department_id: int | None = Query(default=None, gt=0),
    status: Literal["ACTIVE", "INACTIVE", "ON_LEAVE", "ALL"] = "ACTIVE",
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    return db_action(lambda connection: find_employees(connection, q, department_id, status, limit))


@app.get("/api/employees/{emp_id}/profile", response_model=EmployeeProfileResponse,
         tags=["Directory"])
def get_employee_profile(emp_id: int = Path(gt=0)) -> dict[str, Any]:
    return db_action(lambda connection: employee_profile(connection, emp_id))


@app.get("/api/departments", response_model=list[DepartmentResponse], tags=["Directory"])
def get_departments() -> list[dict[str, Any]]:
    return db_action(department_list)


@app.get("/api/projects", response_model=list[ProjectResponse], tags=["Directory"])
def get_projects() -> list[dict[str, Any]]:
    return db_action(project_list)


@app.post("/api/graph/shortest-path", response_model=ShortestPathResponse,
          tags=["SQL Property Graph"])
def post_shortest_path(body: ShortestPathRequest) -> dict[str, Any]:
    return db_action(lambda connection: shortest_path(connection, body))


@app.get("/api/graph/subordinates/{manager_id}", response_model=ComparisonResponse,
         tags=["SQL Property Graph"])
def get_subordinates(manager_id: int = Path(gt=0)) -> dict[str, Any]:
    return db_action(lambda connection: subordinates(connection, manager_id))


@app.get("/api/graph/teammates/{emp_id}", response_model=GraphResponse,
         tags=["SQL Property Graph"])
def get_teammates(emp_id: int = Path(gt=0)) -> dict[str, Any]:
    return db_action(lambda connection: teammates_graph(connection, emp_id))


@app.get("/api/graph/check-teammate", response_model=TeammateCheckResponse,
         tags=["SQL Property Graph"])
def get_check_teammate(
    emp1: int = Query(gt=0), emp2: int = Query(gt=0)
) -> dict[str, Any]:
    return db_action(lambda connection: check_teammate(connection, emp1, emp2))


@app.get("/api/graph/khops/{emp_id}", response_model=GraphResponse,
         tags=["SQL Property Graph"])
def get_khops(
    emp_id: int = Path(gt=0), k: int = Query(default=2, ge=1, le=3)
) -> dict[str, Any]:
    return db_action(lambda connection: khops_graph(connection, emp_id, k))


@app.post("/api/connections", response_model=MutationResponse, status_code=201,
          tags=["Connections & Triggers"])
def create_connection(body: ConnectionCreate) -> dict[str, Any]:
    return db_action(lambda connection: connection_create(connection, body), write=True)


@app.put("/api/connections", response_model=MutationResponse,
         tags=["Connections & Triggers"])
def update_connection(body: ConnectionUpdate) -> dict[str, Any]:
    return db_action(lambda connection: connection_update(connection, body), write=True)


@app.delete("/api/connections", response_model=MutationResponse,
            tags=["Connections & Triggers"])
def delete_connection(body: ConnectionDelete) -> dict[str, Any]:
    return db_action(lambda connection: connection_delete(connection, body), write=True)


@app.post("/api/projects/{project_id}/members", response_model=ProjectMemberResponse,
          status_code=201,
          tags=["Connections & Triggers"])
def post_project_member(project_id: int, body: ProjectMemberCreate) -> dict[str, Any]:
    if project_id <= 0:
        raise HTTPException(status_code=422, detail="project_id phải > 0")
    return db_action(lambda connection: add_project_member(connection, project_id, body), write=True)


@app.get("/api/stats", response_model=StatsResponse, tags=["Statistics & Audit"])
@app.get("/api/stats/total", response_model=StatsResponse, include_in_schema=False)
def get_stats() -> dict[str, Any]:
    return db_action(stats)


@app.get("/api/audit-logs", response_model=list[AuditLogResponse],
         tags=["Statistics & Audit"])
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    action: Literal["INSERT", "UPDATE", "DELETE"] | None = None,
) -> list[dict[str, Any]]:
    return db_action(lambda connection: audit_logs(connection, limit, action))


@app.get("/api/demo/presets", response_model=list[DemoPresetResponse],
         tags=["Statistics & Audit"])
def get_demo_presets() -> list[dict[str, Any]]:
    return demo_presets()


def _openapi_with_bearer():
    """Swagger Authorize works even though auth is enforced in HTTP middleware."""
    if app.openapi_schema is not None:
        return app.openapi_schema
    spec = get_openapi(title=app.title, version=app.version,
                       description=app.description, routes=app.routes)
    spec.setdefault('components', {}).setdefault('securitySchemes', {})['BearerAuth'] = {
        'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'
    }
    for path, operations in spec.get('paths', {}).items():
        if path.startswith('/api/') and path != '/api/live':
            for entry in operations.values():
                if isinstance(entry, dict):
                    entry['security'] = [{'BearerAuth': []}]
    app.openapi_schema = spec
    return spec


app.openapi = _openapi_with_bearer


app.include_router(make_compat_router(db_action))
app.include_router(make_router(db_action))
app.include_router(make_data_router(db_action))

# SPA's index.html is served from / after all registered API routes.
# Replace static/index.html with the built Frontend distribution when ready.
from pathlib import Path as _Path
_STATIC_DIRECTORY = _Path(__file__).resolve().parent / "static"
_STATIC_DIRECTORY.mkdir(parents=True, exist_ok=True)
app.mount("/", StaticFiles(directory=str(_STATIC_DIRECTORY), html=True), name="frontend")
