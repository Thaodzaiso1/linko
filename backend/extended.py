"""Extended CRUD and graph-read API using the existing seven-table Oracle 23ai schema.
All SQL values are bound; user text is never interpolated into SQL identifiers.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

import oracledb
from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from database import query_all, query_one, scalar
from exceptions import api_error, require_found
from crud_v6 import delete_resource


class Body(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class EmployeeCreate(Body):
    full_name: str = Field(min_length=1, max_length=150)
    email: str = Field(min_length=3, max_length=150, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    title: str | None = Field(default=None, max_length=100)
    department_id: int | None = Field(default=None, gt=0)
    hire_date: date | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: Literal['ACTIVE','INACTIVE','ON_LEAVE'] = 'ACTIVE'

class EmployeePatch(Body):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    email: str | None = Field(default=None, min_length=3, max_length=150, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    title: str | None = Field(default=None, max_length=100)
    department_id: int | None = Field(default=None, gt=0)
    hire_date: date | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: Literal['ACTIVE','INACTIVE','ON_LEAVE'] | None = None

class DepartmentCreate(Body):
    department_name: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=100)

class DepartmentPatch(Body):
    department_name: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=100)

class ProjectCreate(Body):
    project_name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal['PLANNING','ACTIVE','ON_HOLD','COMPLETED','CANCELLED'] = 'ACTIVE'
    department_id: int | None = Field(default=None, gt=0)

class ProjectPatch(Body):
    project_name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    start_date: date | None = None
    end_date: date | None = None
    status: Literal['PLANNING','ACTIVE','ON_HOLD','COMPLETED','CANCELLED'] | None = None
    department_id: int | None = Field(default=None, gt=0)

class ManagerSet(Body):
    manager_id: int = Field(gt=0)

class MembershipPatch(Body):
    role: str = Field(min_length=1, max_length=50)

# Dependency injected by main.py to keep one centralized connection/error handler.
def make_router(db_action):
    r = APIRouter(prefix='/api', tags=['Management & network'])

    def select(conn, table, pk, identity):
        # Only trusted call-site table and PK names.
        row = query_one(conn, f'SELECT * FROM {table} WHERE {pk} = :id', {'id': identity})
        require_found(row, f'{table} #{identity}')
        return row

    def insert(conn, table, pk, data):
        keys = list(data)
        binds = {f'v{i}': v for i, v in enumerate(data.values())}
        columns = ', '.join(keys)
        values = ', '.join(':'+k for k in binds)
        with conn.cursor() as cur:
            identity = cur.var(oracledb.NUMBER)
            cur.execute(f'INSERT INTO {table} ({columns}) VALUES ({values}) RETURNING {pk} INTO :new_id',
                        {**binds, 'new_id': identity})
            new_id = int(identity.getvalue()[0])
        return select(conn, table, pk, new_id)

    def patch(conn, table, pk, identity, body):
        changes = body.model_dump(exclude_unset=True, mode='python')
        if not changes:
            raise api_error(400,'EMPTY_PATCH','Không có trường nào cần cập nhật.')
        required = {'employees': {'full_name','email','status'},
                    'departments': {'department_name'},
                    'projects': {'project_name','status'}}[table]
        if any(k in required and v is None for k,v in changes.items()):
            raise api_error(422,'REQUIRED_FIELD','Không được xóa giá trị trường bắt buộc.')
        select(conn, table, pk, identity)
        updates = ', '.join(f'{key} = :p_{key}' for key in changes)
        binds = {f'p_{key}': value for key,value in changes.items()}
        with conn.cursor() as cur:
            cur.execute(f'UPDATE {table} SET {updates} WHERE {pk} = :identity',
                        {**binds,'identity':identity})
        return select(conn, table, pk, identity)

    def remove(conn, kind, identity, cascade=False, confirm=False):
        return delete_resource(conn, kind, identity, cascade=cascade, confirm=confirm)

    @r.get('/employees/{employee_id}')
    def employee_detail(employee_id:int):
        return db_action(lambda c: select(c,'employees','employee_id',employee_id))

    @r.post('/employees',status_code=201)
    def employee_create(body:EmployeeCreate):
        return db_action(lambda c: insert(c,'employees','employee_id',body.model_dump(exclude_none=True)),write=True)

    @r.put('/employees/{employee_id}')
    @r.patch('/employees/{employee_id}')
    def employee_patch(employee_id:int,body:EmployeePatch):
        return db_action(lambda c: patch(c,'employees','employee_id',employee_id,body),write=True)

    @r.delete('/employees/{employee_id}')
    def employee_delete(employee_id:int,cascade:bool=False,confirm:bool=False,hard:bool=False):
        # Soft deletion is safe/default; employee relations remain for historical reports.
        # Hard deletion requires an Admin JWT (DELETE routes) + explicit confirmation.
        def op(c):
            if not hard:
                if cascade or confirm:
                    raise api_error(400,'HARD_REQUIRED','Dùng hard=true để xóa cứng có xác nhận.')
                original=select(c,'employees','employee_id',employee_id)
                with c.cursor() as cur:
                    cur.execute("UPDATE employees SET status='INACTIVE' WHERE employee_id=:id", {'id':employee_id})
                return {'success':True,'soft_deleted':True,'employee_id':employee_id,
                        'previous_status':original['status'],'status':'INACTIVE'}
            if not confirm:
                raise api_error(400,'CONFIRM_REQUIRED','Xóa cứng yêu cầu hard=true&confirm=true.')
            return remove(c,'employee',employee_id,cascade,confirm)
        return db_action(op,write=True)

    @r.get('/departments/{department_id}')
    def department_detail(department_id:int):
        return db_action(lambda c: select(c,'departments','department_id',department_id))

    @r.post('/departments',status_code=201)
    def department_create(body:DepartmentCreate):
        return db_action(lambda c: insert(c,'departments','department_id',body.model_dump(exclude_none=True)),write=True)

    @r.put('/departments/{department_id}')
    @r.patch('/departments/{department_id}')
    def department_patch(department_id:int,body:DepartmentPatch):
        return db_action(lambda c: patch(c,'departments','department_id',department_id,body),write=True)

    @r.delete('/departments/{department_id}')
    def department_delete(department_id:int):
        return db_action(lambda c: remove(c,'department',department_id),write=True)

    @r.get('/projects/{project_id}')
    def project_detail(project_id:int):
        return db_action(lambda c: select(c,'projects','project_id',project_id))

    @r.post('/projects',status_code=201)
    def project_create(body:ProjectCreate):
        if body.start_date and body.end_date and body.end_date < body.start_date:
            raise api_error(422,'INVALID_DATES','Ngày kết thúc phải từ ngày bắt đầu trở đi.')
        return db_action(lambda c: insert(c,'projects','project_id',body.model_dump(exclude_none=True)),write=True)

    @r.put('/projects/{project_id}')
    @r.patch('/projects/{project_id}')
    def project_patch(project_id:int,body:ProjectPatch):
        def op(c):
            original=select(c,'projects','project_id',project_id)
            updates=body.model_dump(exclude_unset=True)
            start=updates.get('start_date',original['start_date'])
            end=updates.get('end_date',original['end_date'])
            if isinstance(start, str): start=date.fromisoformat(start[:10])
            if isinstance(end, str): end=date.fromisoformat(end[:10])
            if start and end and end < start:
                raise api_error(422,'INVALID_DATES','Ngày kết thúc phải từ ngày bắt đầu trở đi.')
            return patch(c,'projects','project_id',project_id,body)
        return db_action(op,write=True)

    @r.delete('/projects/{project_id}')
    def project_delete(project_id:int,cascade:bool=False,confirm:bool=False):
        return db_action(lambda c: remove(c,'project',project_id,cascade,confirm),write=True)

    @r.get('/projects/{project_id}/members')
    def member_list(project_id:int):
        def op(c):
            select(c,'projects','project_id',project_id)
            return query_all(c,'''SELECT pm.employee_id,e.full_name,e.title,pm.role,pm.join_date
                    FROM project_members pm JOIN employees e ON e.employee_id=pm.employee_id
                    WHERE pm.project_id=:id ORDER BY e.full_name''',{'id':project_id})
        return db_action(op)

    @r.patch('/projects/{project_id}/members/{employee_id}')
    def member_patch(project_id:int,employee_id:int,body:MembershipPatch):
        def op(c):
            with c.cursor() as cur:
                cur.execute('''UPDATE project_members SET role=:role
                    WHERE project_id=:pid AND employee_id=:eid''',{'role':body.role,'pid':project_id,'eid':employee_id})
                if cur.rowcount==0:raise api_error(404,'MEMBER_NOT_FOUND','Không tìm thấy thành viên dự án.')
            return {'success':True,'project_id':project_id,'employee_id':employee_id,'role':body.role}
        return db_action(op,write=True)

    @r.delete('/projects/{project_id}/members/{employee_id}')
    def member_delete(project_id:int,employee_id:int):
        def op(c):
            with c.cursor() as cur:
                cur.execute('''DELETE FROM project_members WHERE project_id=:pid AND employee_id=:eid''',
                            {'pid':project_id,'eid':employee_id})
                if cur.rowcount==0:raise api_error(404,'MEMBER_NOT_FOUND','Không tìm thấy thành viên dự án.')
            return {'success':True,'message':'Đã gỡ thành viên; trigger V5 đồng bộ các quan hệ TEAMMATE tự sinh.'}
        return db_action(op,write=True)

    @r.get('/employees/{employee_id}/manager')
    def manager_get(employee_id:int):
        def op(c):
            select(c,'employees','employee_id',employee_id)
            return query_one(c,'''SELECT r.manager_id,e.full_name AS manager_name,r.since_date
                    FROM reports_to r JOIN employees e ON e.employee_id=r.manager_id
                    WHERE r.employee_id=:id''',{'id':employee_id})
        return db_action(op)

    @r.put('/employees/{employee_id}/manager')
    def manager_set(employee_id:int,body:ManagerSet):
        def op(c):
            if employee_id==body.manager_id:
                raise api_error(400,'SELF_MANAGER','Nhân viên không được quản lý chính mình.')
            select(c,'employees','employee_id',employee_id)
            select(c,'employees','employee_id',body.manager_id)
            # Serialize manager changes so two simultaneous API requests cannot
            # both pass the cycle test before committing opposite edges.
            with c.cursor() as lock_cursor:
                lock_cursor.execute('LOCK TABLE reports_to IN SHARE ROW EXCLUSIVE MODE WAIT 5')
            # Walk upwards from proposed manager, reject any existing reporting cycle.
            cycle=scalar(c,'''SELECT COUNT(*) FROM (
                SELECT manager_id FROM reports_to
                START WITH employee_id=:mid
                CONNECT BY NOCYCLE PRIOR manager_id = employee_id
                ) WHERE manager_id=:eid''',{'mid':body.manager_id,'eid':employee_id})
            if int(cycle or 0):
                raise api_error(409,'MANAGEMENT_CYCLE','Phân công này tạo chu trình quản lý.')
            with c.cursor() as cur:
                cur.execute('''MERGE INTO reports_to r USING
                    (SELECT :eid AS eid,:mid AS mid FROM dual) s
                    ON (r.employee_id=s.eid)
                    WHEN MATCHED THEN UPDATE SET r.manager_id=s.mid,r.since_date=SYSDATE
                    WHEN NOT MATCHED THEN INSERT (employee_id,manager_id,since_date)
                    VALUES (s.eid,s.mid,SYSDATE)''',{'eid':employee_id,'mid':body.manager_id})
            return {'success':True,'employee_id':employee_id,'manager_id':body.manager_id}
        return db_action(op,write=True)

    @r.delete('/employees/{employee_id}/manager')
    def manager_delete(employee_id:int):
        def op(c):
            with c.cursor() as cur:
                cur.execute('DELETE FROM reports_to WHERE employee_id=:id',{'id':employee_id})
                if cur.rowcount==0:raise api_error(404,'MANAGER_NOT_FOUND','Nhân viên chưa có quản lý.')
            return {'success':True,'employee_id':employee_id}
        return db_action(op,write=True)

    @r.get('/connections')
    def connection_list(employee_id:int|None=Query(None,gt=0),connection_type:str|None=None,
                        limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0)):
        if connection_type and connection_type not in {'COLLEAGUE','FRIEND','MENTOR','MENTEE','TEAMMATE','FOLLOW'}:
            raise api_error(422,'INVALID_CONNECTION_TYPE','Loại quan hệ không hợp lệ.')
        return db_action(lambda c:query_all(c,'''SELECT k.from_emp,k.to_emp,k.connection_type,k.strength,
            k.since_date,k.notes,a.full_name AS from_name,b.full_name AS to_name
            FROM knows k JOIN employees a ON a.employee_id=k.from_emp
            JOIN employees b ON b.employee_id=k.to_emp
            WHERE (:eid IS NULL OR k.from_emp=:eid OR k.to_emp=:eid)
              AND (:ctype IS NULL OR k.connection_type=:ctype)
            ORDER BY k.from_emp,k.to_emp OFFSET :skip ROWS FETCH NEXT :take ROWS ONLY''',
            {'eid':employee_id,'ctype':connection_type,'skip':offset,'take':limit}))

    @r.get('/graph/overview')
    def graph_overview(department_id:int|None=Query(None,gt=0),limit:int=Query(120,ge=1,le=300)):
        def op(c):
            nodes=query_all(c,'''SELECT employee_id,full_name,title,department_id FROM employees
                WHERE status='ACTIVE' AND (:did IS NULL OR department_id=:did)
                ORDER BY employee_id FETCH FIRST :take ROWS ONLY''',{'did':department_id,'take':limit})
            ids=[int(n['employee_id']) for n in nodes]
            if not ids:return {'nodes':[],'edges':[],'elements':{'nodes':[],'edges':[]}}
            # Query ONLY the selected IDs (not <= maxid) and limit graph payload.
            # IDs are bound values, never interpolated from client text.
            placeholders = ', '.join(f':id{i}' for i in range(len(ids)))
            params = {f'id{i}': employee_id for i, employee_id in enumerate(ids)}
            sql = f"""SELECT relation_type, source_id, target_id, detail FROM (
                SELECT 'Knows' AS relation_type, k.from_emp AS source_id,
                       k.to_emp AS target_id, k.connection_type AS detail
                FROM knows k WHERE k.from_emp IN ({placeholders}) AND k.to_emp IN ({placeholders})
                UNION ALL
                SELECT 'ReportsTo', r.employee_id, r.manager_id, 'REPORTS_TO'
                FROM reports_to r WHERE r.employee_id IN ({placeholders})
                    AND r.manager_id IN ({placeholders})
            ) ORDER BY relation_type, source_id, target_id FETCH FIRST :edge_limit ROWS ONLY"""
            edges = query_all(c, sql, {**params, 'edge_limit': 5001})
            truncated_edges = len(edges) > 5000
            edges = edges[:5000]
            return {'nodes':[dict(n,id=n['employee_id'],label=n['full_name'],group=n['department_id']) for n in nodes],
                    'truncated_edges':truncated_edges,
                    'edges':[dict(e,id=i+1,**{'from':e['source_id'],'to':e['target_id']},label=e['detail']) for i,e in enumerate(edges)],
                    'elements':{'nodes':[{'data':{'id':f"emp_{n['employee_id']}",'label':n['full_name'],**n}} for n in nodes],
                                'edges':[{'data':{'id':f"edge_{i}",'source':f"emp_{e['source_id']}",
                                                    'target':f"emp_{e['target_id']}",**e}} for i,e in enumerate(edges)]}}
        return db_action(op)

    @r.get('/stats/departments')
    def stats_departments():
        return db_action(lambda c:query_all(c,'''SELECT d.department_id,d.department_name,
            COUNT(DISTINCT e.employee_id) AS employee_count,
            COUNT(DISTINCT CASE WHEN e.status='ACTIVE' THEN e.employee_id END) AS active_count
            FROM departments d LEFT JOIN employees e ON e.department_id=d.department_id
            GROUP BY d.department_id,d.department_name ORDER BY active_count DESC,d.department_id'''))

    @r.get('/stats/top-connectors')
    def top_connectors(limit:int=Query(10,ge=1,le=100)):
        return db_action(lambda c:query_all(c,'''SELECT e.employee_id,e.full_name,d.department_name,
            (SELECT COUNT(*) FROM knows k WHERE k.from_emp=e.employee_id) AS outgoing,
            (SELECT COUNT(*) FROM knows k WHERE k.to_emp=e.employee_id) AS incoming,
            (SELECT COUNT(*) FROM project_members p WHERE p.employee_id=e.employee_id) AS projects
            FROM employees e LEFT JOIN departments d ON d.department_id=e.department_id
            WHERE e.status='ACTIVE'
            ORDER BY 4 DESC,5 DESC,e.employee_id
            FETCH FIRST :take ROWS ONLY''',{'take':limit}))
    @r.get('/network/integrity')
    def network_integrity():
        """Detect orphaned automatic edges and missing pairs after migration.

        Manual friendships are valid even if people share a project, so any
        existing Knows record counts as an intentional relationship.
        """
        def op(c):
            stale = int(scalar(c, """SELECT COUNT(*) FROM knows k
                WHERE k.connection_type='TEAMMATE'
                  AND k.notes LIKE 'Auto-created from project %'
                  AND NOT EXISTS (
                    SELECT 1 FROM project_members a JOIN project_members b
                    ON a.project_id=b.project_id
                    WHERE a.employee_id=k.from_emp AND b.employee_id=k.to_emp)""") or 0)
            missing = int(scalar(c, """SELECT COUNT(*) FROM (
                SELECT DISTINCT a.employee_id AS from_emp,b.employee_id AS to_emp
                FROM project_members a JOIN project_members b
                ON a.project_id=b.project_id AND a.employee_id<>b.employee_id
            ) pair WHERE NOT EXISTS (
                SELECT 1 FROM knows k
                WHERE k.from_emp=pair.from_emp AND k.to_emp=pair.to_emp)""") or 0)
            return {'status': 'ok' if not stale and not missing else 'needs_reconciliation',
                    'stale_auto_teammate_edges': stale,
                    'missing_shared_project_edges': missing,
                    'repair_sql': 'sql/setup/08_reconcile_teammates.sql' if stale or missing else None}
        return db_action(op)

    @r.get('/stats/cross-department')
    def cross_department_stats(limit:int=Query(30,ge=1,le=100)):
        """Group directed cross-department Knows edges by unordered department pair."""
        return db_action(lambda c:query_all(c, """SELECT
           d1.department_id AS source_department_id,
           d1.department_name AS source_department,
           d2.department_id AS target_department_id,
           d2.department_name AS target_department,
           COUNT(*) AS relation_count
           FROM knows k JOIN employees e1 ON e1.employee_id=k.from_emp
             JOIN employees e2 ON e2.employee_id=k.to_emp
             JOIN departments d1 ON d1.department_id=LEAST(e1.department_id,e2.department_id)
             JOIN departments d2 ON d2.department_id=GREATEST(e1.department_id,e2.department_id)
           WHERE e1.department_id<>e2.department_id AND e1.status='ACTIVE'
             AND e2.status='ACTIVE'
           GROUP BY d1.department_id,d1.department_name,
                    d2.department_id,d2.department_name
           ORDER BY relation_count DESC,source_department_id,target_department_id
           FETCH FIRST :take ROWS ONLY""", {'take':limit}))

    @r.get('/stats/project-collaboration')
    def project_collaboration(limit:int=Query(30,ge=1,le=100)):
        """Project members and cross-team diversity for HR dashboard."""
        return db_action(lambda c:query_all(c, """SELECT
            p.project_id,p.project_name,p.status,
            COUNT(pm.employee_id) AS member_count,
            COUNT(DISTINCT e.department_id) AS department_count
            FROM projects p LEFT JOIN project_members pm ON pm.project_id=p.project_id
            LEFT JOIN employees e ON e.employee_id=pm.employee_id
            GROUP BY p.project_id,p.project_name,p.status
            ORDER BY member_count DESC,p.project_id
            FETCH FIRST :take ROWS ONLY""", {'take':limit}))

    return r
