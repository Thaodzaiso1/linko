"""V6 safe data editing and removal, all transactions owned by main.db_action.

No new tables and no in-memory fallback. Every operation writes to Oracle's
existing 7 tables; PL/SQL triggers continue to own TEAMMATE synchronization.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Path
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from database import query_all, query_one, scalar
from exceptions import api_error, require_found
from graph_service import connection_update, connection_delete
from schemas import ConnectionUpdate, ConnectionDelete


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StatusChange(StrictBody):
    status: Literal["ACTIVE", "INACTIVE", "ON_LEAVE"]


class BulkEmployeeStatus(StrictBody):
    employee_ids: list[int] = Field(min_length=1, max_length=100)
    status: Literal["ACTIVE", "INACTIVE", "ON_LEAVE"]

    @field_validator("employee_ids")
    @classmethod
    def validate_ids(cls, items):
        if any(x <= 0 for x in items) or len(set(items)) != len(items):
            raise ValueError("employee_ids phải dương và không trùng lặp")
        return items


class TransferDepartment(StrictBody):
    target_department_id: int = Field(gt=0)
    move_employees: bool = True
    move_projects: bool = True

    @model_validator(mode="after")
    def at_least_one(self):
        if not (self.move_employees or self.move_projects):
            raise ValueError("Cần chuyển nhân viên hoặc dự án")
        return self


class MemberUpsert(StrictBody):
    role: str = Field(min_length=1, max_length=50)
    join_date: date | None = None


class ConnectionEdit(StrictBody):
    connection_type: Literal["COLLEAGUE", "FRIEND", "MENTOR", "MENTEE", "TEAMMATE", "FOLLOW"] | None = None
    strength: Decimal | None = Field(default=None, ge=0, le=5, decimal_places=2)
    notes: str | None = Field(default=None, max_length=200)


def _existing(connection, table: str, pk: str, identity: int):
    # Called exclusively with fixed table/key literals from below.
    record = query_one(connection, f"SELECT * FROM {table} WHERE {pk}=:id", {"id": identity})
    require_found(record, f"{table} #{identity}")
    return record


def _impact(connection, kind: str, identity: int) -> dict:
    tables = {
        "employee": ("employees", "employee_id"),
        "project": ("projects", "project_id"),
        "department": ("departments", "department_id"),
    }
    if kind not in tables:
        raise ValueError("Loại dữ liệu không hợp lệ")
    table, pk = tables[kind]
    original = _existing(connection, table, pk, identity)
    sql = {
        "employee": """SELECT
            (SELECT COUNT(*) FROM project_members WHERE employee_id=:id) AS memberships,
            (SELECT COUNT(*) FROM knows WHERE from_emp=:id OR to_emp=:id) AS connections,
            (SELECT COUNT(*) FROM reports_to WHERE employee_id=:id) AS own_manager,
            (SELECT COUNT(*) FROM reports_to WHERE manager_id=:id) AS direct_reports
            FROM dual""",
        "project": """SELECT (SELECT COUNT(*) FROM project_members WHERE project_id=:id) AS memberships FROM dual""",
        "department": """SELECT
            (SELECT COUNT(*) FROM employees WHERE department_id=:id) AS employees,
            (SELECT COUNT(*) FROM projects WHERE department_id=:id) AS projects
            FROM dual""",
    }[kind]
    counts = query_one(connection, sql, {"id": identity}) or {}
    counts = {key: int(v or 0) for key, v in counts.items()}
    return {"type": kind, "id": identity, "record": original,
            "dependencies": counts, "has_dependencies": any(counts.values()),
            "cascade_supported": kind in {"employee", "project"},
            "warning": "Xóa cứng không thể hoàn tác; audit_log KNOWS vẫn được giữ."}


def _delete(connection, kind: str, identity: int, cascade: bool = False, confirm: bool = False) -> dict:
    """Explicit cascade never silently deletes employees belonging to a department."""
    if cascade and not confirm:
        raise api_error(400, "CONFIRM_REQUIRED", "Xóa liên đới yêu cầu cascade=true&confirm=true.")
    # Forbid child creation during deletion by locking the parent row first.
    table, pk = {
        "employee": ("employees", "employee_id"),
        "project": ("projects", "project_id"),
        "department": ("departments", "department_id"),
    }[kind]
    with connection.cursor() as cur:
        cur.execute(f"SELECT {pk} FROM {table} WHERE {pk}=:id FOR UPDATE", {"id": identity})
        if cur.fetchone() is None:
            raise api_error(404, "NOT_FOUND", f"Không tìm thấy {kind} #{identity}.")

    impact = _impact(connection, kind, identity)
    if impact["has_dependencies"] and not cascade:
        raise api_error(409, "DELETE_HAS_DEPENDENCIES",
                        f"Không thể xóa {kind} #{identity}: đang được tham chiếu {impact['dependencies']}. "
                        f"Xem /api/data/{kind}s/{identity}/delete-impact.")
    if kind == "employee" and impact["dependencies"].get("direct_reports", 0):
        raise api_error(409,"REASSIGN_REPORTS_FIRST",
                        "Không xóa cứng quản lý còn cấp dưới; gán quản lý mới cho từng người trước.")
    if kind == "department" and impact["has_dependencies"]:
        raise api_error(409, "TRANSFER_FIRST",
                        "Không xóa phòng ban còn nhân sự/dự án; hãy chuyển dữ liệu sang phòng ban khác trước.")

    with connection.cursor() as cur:
        if cascade and kind == "employee":
            # Trigger V5 reconciles auto TEAMMATE records after member deletion.
            cur.execute("DELETE FROM project_members WHERE employee_id=:id", {"id": identity})
            cur.execute("DELETE FROM knows WHERE from_emp=:id OR to_emp=:id", {"id": identity})
            cur.execute("DELETE FROM reports_to WHERE employee_id=:id OR manager_id=:id", {"id": identity})
        elif cascade and kind == "project":
            cur.execute("DELETE FROM project_members WHERE project_id=:id", {"id": identity})
        cur.execute(f"DELETE FROM {table} WHERE {pk}=:id", {"id": identity})
        deleted = cur.rowcount
    return {"success": True, "deleted": deleted, "type": kind, "deleted_id": identity,
            "cascade": cascade, "previous_dependencies": impact["dependencies"]}


def delete_resource(connection, kind: str, identity: int, cascade: bool = False, confirm: bool = False):
    return _delete(connection, kind, identity, cascade, confirm)


def make_router(db_action):
    router = APIRouter(prefix="/api/data", tags=["Data management V6"])

    @router.get("/employees/{employee_id}/delete-impact")
    def impact_employee(employee_id: int = Path(gt=0)):
        return db_action(lambda c: _impact(c, "employee", employee_id))

    @router.get("/projects/{project_id}/delete-impact")
    def impact_project(project_id: int = Path(gt=0)):
        return db_action(lambda c: _impact(c, "project", project_id))

    @router.get("/departments/{department_id}/delete-impact")
    def impact_department(department_id: int = Path(gt=0)):
        return db_action(lambda c: _impact(c, "department", department_id))

    @router.patch("/employees/{employee_id}/status")
    def change_employee_status(employee_id: int, body: StatusChange):
        def op(c):
            _existing(c, "employees", "employee_id", employee_id)
            with c.cursor() as cur:
                cur.execute("UPDATE employees SET status=:status WHERE employee_id=:id",
                            {"status": body.status, "id": employee_id})
            return _existing(c, "employees", "employee_id", employee_id)
        return db_action(op, write=True)

    @router.post("/employees/bulk-status")
    def bulk_status(body: BulkEmployeeStatus):
        def op(c):
            ids = body.employee_ids
            binds = {f"e{i}": value for i, value in enumerate(ids)}
            placeholders = ",".join(":" + k for k in binds)
            # All-or-nothing: validate entire selection prior to writing.
            with c.cursor() as cur:
                cur.execute(f"SELECT employee_id FROM employees WHERE employee_id IN ({placeholders}) FOR UPDATE", binds)
                found = {int(r[0]) for r in cur.fetchall()}
                absent = sorted(set(ids) - found)
                if absent:
                    raise api_error(404, "EMPLOYEES_NOT_FOUND", f"Không tìm thấy employee_ids: {absent}")
                cur.execute(f"UPDATE employees SET status=:status WHERE employee_id IN ({placeholders})",
                            {**binds, "status": body.status})
                affected = cur.rowcount
            return {"success": True, "updated": affected, "employee_ids": ids, "status": body.status}
        return db_action(op, write=True)

    @router.post("/departments/{department_id}/transfer")
    def transfer_department(department_id: int, body: TransferDepartment):
        def op(c):
            if department_id == body.target_department_id:
                raise api_error(400, "SAME_DEPARTMENT", "Phòng chuyển và nhận phải khác nhau.")
            _existing(c, "departments", "department_id", department_id)
            _existing(c, "departments", "department_id", body.target_department_id)
            # Lock parent rows to serialize competing reassignments/deletion.
            with c.cursor() as cur:
                cur.execute("SELECT department_id FROM departments WHERE department_id IN (:from_id,:to_id) FOR UPDATE",
                            {"from_id": department_id, "to_id": body.target_department_id})
                employee_count = project_count = 0
                if body.move_employees:
                    cur.execute("UPDATE employees SET department_id=:to_id WHERE department_id=:from_id",
                                {"from_id": department_id, "to_id": body.target_department_id})
                    employee_count = cur.rowcount
                if body.move_projects:
                    cur.execute("UPDATE projects SET department_id=:to_id WHERE department_id=:from_id",
                                {"from_id": department_id, "to_id": body.target_department_id})
                    project_count = cur.rowcount
            return {"success": True, "from_department_id": department_id,
                    "target_department_id": body.target_department_id,
                    "moved_employees": employee_count, "moved_projects": project_count}
        return db_action(op, write=True)

    @router.put("/projects/{project_id}/members/{employee_id}")
    def upsert_member(project_id: int, employee_id: int, body: MemberUpsert):
        def op(c):
            project = _existing(c, "projects", "project_id", project_id)
            employee = _existing(c, "employees", "employee_id", employee_id)
            if employee["status"] != "ACTIVE":
                raise api_error(409, "INACTIVE_EMPLOYEE", "Chỉ gán nhân viên ACTIVE vào dự án.")
            # Existing projects can have their member roles corrected even if completed.
            with c.cursor() as cur:
                cur.execute("SELECT employee_id FROM project_members WHERE project_id=:pid AND employee_id=:eid FOR UPDATE",
                            {"pid": project_id, "eid": employee_id})
                exists = cur.fetchone() is not None
                if not exists and project["status"] in {"COMPLETED", "CANCELLED"}:
                    raise api_error(409, "PROJECT_CLOSED", "Không thêm người vào dự án đã hoàn tất/hủy.")
                if exists:
                    cur.execute("""UPDATE project_members SET role=:role,
                        join_date=COALESCE(CAST(:joined AS DATE),join_date)
                        WHERE project_id=:pid AND employee_id=:eid""",
                        {"role": body.role, "joined": body.join_date, "pid": project_id, "eid": employee_id})
                else:
                    cur.execute("""INSERT INTO project_members(employee_id,project_id,role,join_date)
                        VALUES(:eid,:pid,:role,COALESCE(CAST(:joined AS DATE),SYSDATE))""",
                        {"eid": employee_id, "pid": project_id, "role": body.role, "joined": body.join_date})
            result = query_one(c, "SELECT employee_id,project_id,role,join_date FROM project_members WHERE project_id=:pid AND employee_id=:eid",
                               {"pid": project_id, "eid": employee_id})
            return {"success": True, "created": not exists, "record": result}
        return db_action(op, write=True)

    @router.get("/connections/{from_emp}/{to_emp}")
    def connection_detail(from_emp: int, to_emp: int):
        def op(c):
            record = query_one(c, """SELECT from_emp,to_emp,connection_type,strength,notes,since_date
                FROM knows WHERE from_emp=:a AND to_emp=:b""", {"a":from_emp, "b":to_emp})
            require_found(record, f"KNOWS {from_emp}->{to_emp}")
            return record
        return db_action(op)

    @router.patch("/connections/{from_emp}/{to_emp}")
    def edit_connection(from_emp: int, to_emp: int, body: ConnectionEdit):
        if not body.model_fields_set:
            raise api_error(400, "EMPTY_PATCH", "Cần nhập trường để sửa.")
        return db_action(lambda c: connection_update(c, ConnectionUpdate(
            from_emp=from_emp, to_emp=to_emp, **body.model_dump(exclude_unset=True))), write=True)

    @router.delete("/connections/{from_emp}/{to_emp}")
    def remove_connection(from_emp: int, to_emp: int):
        return db_action(lambda c: connection_delete(c, ConnectionDelete(from_emp=from_emp, to_emp=to_emp)), write=True)

    return router
