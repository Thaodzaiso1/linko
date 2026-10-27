"""Offline V6 contract tests. Does not claim a live Oracle round trip."""
import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_contract  # Creates minimal oracledb test stub if not installed.

from fastapi.testclient import TestClient
from pydantic import ValidationError
import crud_v6
import graph_service
import main


class Cursor:
    def __init__(self, rows=None, rowcount=1):
        self.rows = rows or []
        self.rowcount = rowcount
        self.calls = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, sql, binds=None):
        self.calls.append((sql, binds or {}))
        self.rowcount = len(self.rows) if sql.strip().upper().startswith('UPDATE EMPLOYEES') else 1
    def fetchone(self): return self.rows[0] if self.rows else None
    def fetchall(self): return self.rows


class Connection:
    def __init__(self, rows=None): self.cur=Cursor(rows=rows)
    def cursor(self): return self.cur


class CrudV6Tests(unittest.TestCase):
    def test_routes_exposed(self):
        client=TestClient(main.app)
        openapi=client.get('/openapi.json').json()
        paths=openapi['paths']
        required={
          '/api/data/employees/bulk-status': 'post',
          '/api/data/employees/{employee_id}/status': 'patch',
          '/api/data/employees/{employee_id}/delete-impact': 'get',
          '/api/data/projects/{project_id}/delete-impact': 'get',
          '/api/data/departments/{department_id}/delete-impact': 'get',
          '/api/data/departments/{department_id}/transfer': 'post',
          '/api/data/projects/{project_id}/members/{employee_id}': 'put',
          '/api/data/connections/{from_emp}/{to_emp}': 'patch',
        }
        for path,verb in required.items():
            self.assertIn(verb, paths[path])
        self.assertIn('cascade',paths['/api/employees/{employee_id}']['delete']['parameters'][1]['name'] if False else [p['name'] for p in paths['/api/employees/{employee_id}']['delete']['parameters']])
        self.assertEqual(openapi['info']['version'],'7.0.0')

    def test_pydantic_bulk_and_conflict_validation(self):
        for invalid in ([1,1],[1,-2],[],list(range(1,102))):
            with self.subTest(invalid_length=len(invalid)):
                with self.assertRaises(ValidationError):
                    crud_v6.BulkEmployeeStatus(employee_ids=invalid,status='ACTIVE')
        with self.assertRaises(ValidationError):
            crud_v6.TransferDepartment(target_department_id=4,move_employees=False,move_projects=False)
        with self.assertRaises(ValidationError):
            crud_v6.MemberUpsert(role='a'*51)

    def test_write_requires_oracle_if_db_unavailable(self):
        with patch.object(main, 'get_connection', side_effect=RuntimeError('test DB missing')):
            result=TestClient(main.app).post('/api/data/employees/bulk-status',json={'employee_ids':[1],'status':'INACTIVE'})
        self.assertEqual(result.status_code,503)
        self.assertEqual(result.json()['detail']['code'],'DATABASE_UNAVAILABLE')

    def test_delete_guard_requires_cascade_and_explicit_confirmation(self):
        connection=Connection(rows=[(12,)])
        impact={'dependencies':{'memberships':2,'connections':5},'has_dependencies':True}
        with patch.object(crud_v6,'_impact',return_value=impact):
            with self.assertRaises(main.HTTPException) as exc:
                crud_v6.delete_resource(connection,'employee',12)
            self.assertEqual(exc.exception.status_code,409)
            with self.assertRaises(main.HTTPException) as exc:
                crud_v6.delete_resource(connection,'employee',12,cascade=True)
            self.assertEqual(exc.exception.status_code,400)
            outcome=crud_v6.delete_resource(connection,'employee',12,cascade=True,confirm=True)
        self.assertTrue(outcome['success'])
        sqls=[entry[0].strip() for entry in connection.cur.calls]
        self.assertEqual([q.split()[2] for q in sqls if q.startswith('DELETE FROM')],
                         ['project_members','knows','reports_to','employees'])

    def test_project_cascade_removes_membership_before_project(self):
        connection=Connection(rows=[(4,)])
        with patch.object(crud_v6,'_impact',return_value={'dependencies':{'memberships':2},'has_dependencies':True}):
            crud_v6.delete_resource(connection,'project',4,cascade=True,confirm=True)
        actions=[sql.strip() for sql,_ in connection.cur.calls if sql.strip().startswith('DELETE FROM')]
        self.assertEqual(actions, ['DELETE FROM project_members WHERE project_id=:id',
                                   'DELETE FROM projects WHERE project_id=:id'])

    def test_department_never_cascades_to_employees(self):
        connection=Connection(rows=[(2,)])
        with patch.object(crud_v6,'_impact',return_value={'dependencies':{'employees':1,'projects':1},'has_dependencies':True}):
            with self.assertRaises(main.HTTPException) as exc:
                crud_v6.delete_resource(connection,'department',2,cascade=True,confirm=True)
        self.assertEqual(exc.exception.status_code,409)
        self.assertNotIn('DELETE FROM',str(connection.cur.calls))

    def test_auto_teammate_cannot_be_edited_or_deleted_manually(self):
        connection=Connection(rows=[('TEAMMATE','Auto-created from project 7')])
        with self.assertRaises(main.HTTPException) as exc:
            graph_service._check_connection_editable(connection,1,2)
        self.assertEqual(exc.exception.status_code,409)
        self.assertEqual(exc.exception.detail['code'],'AUTO_TEAMMATE_PROTECTED')
        with self.assertRaises(main.HTTPException):
            graph_service._check_manual_notes('Auto-created from project 77')
        connection=Connection(rows=[('FRIEND',None)])
        self.assertIsNone(graph_service._check_connection_editable(connection,1,2))

    def test_bulk_status_no_missing_employee(self):
        conn=Connection(rows=[(7,)])
        # Call V6 router endpoint while db_action keeps the same transaction semantics.
        router=crud_v6.make_router(lambda fn,write=False: fn(conn))
        endpoint=next(r.endpoint for r in router.routes if r.path=='/api/data/employees/bulk-status')
        with self.assertRaises(main.HTTPException) as exc:
            endpoint(crud_v6.BulkEmployeeStatus(employee_ids=[7,8],status='INACTIVE'))
        self.assertEqual(exc.exception.status_code,404)
        self.assertFalse(any(sql.strip().startswith('UPDATE') for sql,_ in conn.cur.calls))

    def test_member_upsert_rejects_closed_projects_for_new_members(self):
        conn=Connection(rows=[])
        router=crud_v6.make_router(lambda fn,write=False: fn(conn))
        endpoint=next(r.endpoint for r in router.routes if r.path=='/api/data/projects/{project_id}/members/{employee_id}')
        def stub_existing(_,table,pk,identity):
            return {'status':'ACTIVE'} if table=='employees' else {'status':'COMPLETED'}
        with patch.object(crud_v6,'_existing',side_effect=stub_existing):
            with self.assertRaises(main.HTTPException) as exc:
                endpoint(4,5,crud_v6.MemberUpsert(role='MEMBER'))
        self.assertEqual(exc.exception.detail['code'],'PROJECT_CLOSED')


if __name__=='__main__': unittest.main()
