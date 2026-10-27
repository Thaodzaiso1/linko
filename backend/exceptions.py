"""Stable Vietnamese HTTP error contract for Oracle and business exceptions."""

from __future__ import annotations

import logging
import re

import oracledb
from fastapi import HTTPException

logger = logging.getLogger(__name__)

ERRORS: dict[str, tuple[int, str, str]] = {
    "ORA-20001": (400, "SELF_CONNECTION", "Không thể tạo quan hệ kết nối với chính mình."),
    "ORA-20002": (404, "EMPLOYEE_NOT_FOUND", "Một hoặc cả hai nhân viên không tồn tại hoặc không ở trạng thái ACTIVE."),
    "ORA-20003": (409, "CONNECTION_EXISTS", "Quan hệ kết nối đã tồn tại giữa hai nhân viên này."),
    "ORA-02290": (400, "CHECK_VIOLATION", "Dữ liệu vi phạm ràng buộc toàn vẹn (trạng thái, độ mạnh 0-5 hoặc tự kết nối)."),
    "ORA-00001": (409, "DUPLICATE_RECORD", "Bản ghi hoặc email/kết nối đã tồn tại."),
    "ORA-02291": (404, "FOREIGN_KEY_NOT_FOUND", "Đối tượng tham chiếu (Nhân viên/Phòng ban/Dự án) không tồn tại."),
    "ORA-02292": (409, "RECORD_IN_USE", "Không thể xóa đối tượng vì đang được các bản ghi khác tham chiếu."),
    "ORA-04091": (500, "MUTATING_TABLE", "Trigger project_members đang gặp lỗi mutating table. Cài bản trigger thay thế trong sql/setup/05_fix_auto_teammate_trigger.sql."),
}


def api_error(http_status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


def handle_oracle_error(error: Exception) -> None:
    """Raise HTTPException; also recognizes ORA codes wrapped by ORA-20099."""
    raw = str(error)
    db_error = error.args[0] if error.args else None
    oracle_code = getattr(db_error, "code", None)
    if oracle_code is not None:
        raw = f"ORA-{int(oracle_code):05d}: {raw}"

    for token, (status, code, message) in ERRORS.items():
        if token in raw:
            raise api_error(status, code, message) from error
    logger.exception("Database operation failed: %s", raw)
    if any(token in raw for token in ("DPY-4005", "DPY-6005", "DPY-6000", "ORA-12541", "ORA-12154", "ORA-01017", "ORA-03113")):
        raise api_error(503, "DATABASE_UNAVAILABLE", "Không kết nối được Oracle. Kiểm tra host, service và tài khoản DB.") from error
    # Avoid leaking credentials, PDB names, table contents, or raw SQL to clients.
    raise api_error(500, "DATABASE_ERROR", "Lỗi Oracle. Xem log backend để biết chi tiết.") from error


def require_found(value: object | None, description: str) -> None:
    if value is None:
        raise api_error(404, "NOT_FOUND", f"Không tìm thấy {description}.")
