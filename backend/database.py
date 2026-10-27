"""Oracle 23ai Thin Mode: pooled connections and database result helpers.

Use a synchronous pool with standard `def` FastAPI endpoints, which FastAPI
runs on a worker thread. Each request acquires a connection and returns it to
the pool when finished. No Oracle Instant Client is required.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any, Iterator, Mapping

import oracledb
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")
oracledb.enable_thin_mode()

logger = logging.getLogger(__name__)
_pool: oracledb.ConnectionPool | None = None
_pool_lock = Lock()


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Chưa cấu hình {name}; xem .env.example")
    return value


def initialize_pool() -> None:
    """Create a real Oracle pool. No mock/fallback DB is ever used."""
    global _pool
    if _pool is not None:
        return
    with _pool_lock:
        if _pool is not None:
            return
        _initialize_pool_unlocked()


def _initialize_pool_unlocked() -> None:
    global _pool
    port = int(os.getenv("DB_PORT", "1521"))
    if not 1 <= port <= 65535:
        raise RuntimeError("DB_PORT phải nằm trong khoảng 1..65535")

    min_size = int(os.getenv("DB_POOL_MIN", "1"))
    max_size = int(os.getenv("DB_POOL_MAX", "8"))
    increment = int(os.getenv("DB_POOL_INCREMENT", "1"))
    if not (0 <= min_size <= max_size and max_size >= 1 and increment >= 1):
        raise RuntimeError("Thông số kích thước connection pool không hợp lệ")

    dsn = oracledb.makedsn(
        required_env("DB_HOST"), port, service_name=os.getenv("DB_SERVICE", "FREEPDB1")
    )
    pool = oracledb.create_pool(
        user=required_env("DB_USER"),
        password=required_env("DB_PASSWORD"),
        dsn=dsn,
        min=min_size,
        max=max_size,
        increment=increment,
        getmode=oracledb.POOL_GETMODE_WAIT,
        wait_timeout=int(os.getenv("DB_POOL_WAIT_TIMEOUT", "10000")),
        ping_interval=60,
    )
    try:
        # Thin pool startup can be asynchronous; acquire() forces a real check.
        with pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM dual")
                if cursor.fetchone()[0] != 1:
                    raise RuntimeError("Không thể xác nhận kết nối Oracle")
    except Exception:
        pool.close(force=True)
        raise
    _pool = pool
    logger.info("Oracle Thin connection pool initialized")


def close_pool() -> None:
    global _pool
    if _pool is not None:
        try:
            _pool.close(force=True)
        finally:
            _pool = None
    logger.info("Oracle Thin connection pool closed")


@contextmanager
def get_connection() -> Iterator[oracledb.Connection]:
    if _pool is None:
        initialize_pool()
    with _pool.acquire() as connection:
        yield connection


def json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, oracledb.LOB):
        return value.read()
    return value


def cursor_rows(cursor: oracledb.Cursor) -> list[dict[str, Any]]:
    """Consume rows while the cursor and its parent connection are open."""
    if cursor.description is None:
        return []
    names = [column[0].lower() for column in cursor.description]
    return [
        {name: json_safe(value) for name, value in zip(names, row)}
        for row in cursor.fetchall()
    ]


def query_all(
    connection: oracledb.Connection,
    sql: str,
    binds: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, dict(binds or {}))
        return cursor_rows(cursor)


def query_one(
    connection: oracledb.Connection,
    sql: str,
    binds: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    rows = query_all(connection, sql, binds)
    return rows[0] if rows else None


def scalar(
    connection: oracledb.Connection,
    sql: str,
    binds: Mapping[str, Any] | None = None,
) -> Any:
    with connection.cursor() as cursor:
        cursor.execute(sql, dict(binds or {}))
        row = cursor.fetchone()
        return json_safe(row[0]) if row else None


def call_refcursor(
    connection: oracledb.Connection, procedure_name: str, identifier: int
) -> list[dict[str, Any]]:
    """Call a fixed, trusted procedure name exposing OUT SYS_REFCURSOR."""
    # Never pass arbitrary client input as the PL/SQL procedure name.
    allowed = {"pkg_social_network.get_teammates", "sp_get_org_tree"}
    if procedure_name not in allowed:
        raise ValueError("Procedure không được hỗ trợ")
    with connection.cursor() as cursor:
        with connection.cursor() as out_cursor:
            cursor.callproc(procedure_name, [identifier, out_cursor])
            return cursor_rows(out_cursor)
