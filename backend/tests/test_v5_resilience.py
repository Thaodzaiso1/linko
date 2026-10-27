"""V5 contract tests use a fake transaction ONLY in tests; no mock DB in server."""
import sys
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_contract  # Only needed if real oracledb dependency absent during offline tests.
import main
from fastapi.testclient import TestClient

class TransactionStub:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1

class V5ResilienceTests(unittest.TestCase):
    def test_all_or_nothing_commit(self):
        conn = TransactionStub()
        @contextmanager
        def fake_get_connection(): yield conn
        with patch.object(main, 'get_connection', fake_get_connection):
            result=main.db_action(lambda c: {'success':True}, write=True)
        self.assertTrue(result['success'])
        self.assertEqual(conn.commits, 1)
        self.assertEqual(conn.rollbacks, 0)

    def test_error_rolls_back(self):
        conn=TransactionStub()
        @contextmanager
        def fake_get_connection(): yield conn
        def fail(c): raise main.api_error(409, 'TEST', 'rollback')
        with patch.object(main, 'get_connection', fake_get_connection):
            with self.assertRaises(main.HTTPException) as ex:
                main.db_action(fail, write=True)
        self.assertEqual(ex.exception.status_code,409)
        self.assertEqual(conn.commits,0)
        self.assertEqual(conn.rollbacks,1)

    def test_failed_commit_rolls_back(self):
        conn=TransactionStub()
        def fail_commit(): raise RuntimeError('commit failure')
        conn.commit=fail_commit
        @contextmanager
        def fake_get_connection():yield conn
        with patch.object(main,'get_connection',fake_get_connection):
            with self.assertRaises(main.HTTPException) as ex:
                main.db_action(lambda _: {'success':True}, write=True)
        self.assertEqual(ex.exception.status_code,503)
        self.assertEqual(conn.rollbacks,1)

    def test_read_is_not_committed(self):
        conn=TransactionStub()
        @contextmanager
        def fake_get_connection():yield conn
        with patch.object(main,'get_connection',fake_get_connection):
            main.db_action(lambda _: 7)
        self.assertEqual(conn.commits,0)
        self.assertEqual(conn.rollbacks,1)

    def test_v7_security_writes_require_role_in_local_mode(self):
        import jwt
        from datetime import datetime, timedelta, timezone
        secret='security-test-key-is-over-thirty-two-characters-long'
        now=datetime.now(timezone.utc)
        def token(role):
            return jwt.encode({'sub':'tester','roles':[role], 'iss':'linko-local','aud':'linko-api',
                'iat':now, 'exp':now+timedelta(minutes=5)},secret,algorithm='HS256')
        with patch.dict(os.environ,{'AUTH_MODE':'local','JWT_SECRET':secret}):
            client=TestClient(main.app)
            missing=client.post('/api/employees',json={'full_name':'Test','email':'test@example.com'})
            self.assertEqual(missing.status_code,401)
            with patch.object(main,'get_connection',side_effect=RuntimeError('offline')):
                read=client.post('/api/graph/shortest-path',json={'source_id':1,'target_id':2},
                    headers={'Authorization':'Bearer '+token('employee')})
                self.assertEqual(read.status_code,503)
                forbidden=client.post('/api/employees',json={'full_name':'Test','email':'test@example.com'},
                    headers={'Authorization':'Bearer '+token('employee')})
                self.assertEqual(forbidden.status_code,403)
                allowed=client.post('/api/employees',json={'full_name':'Test','email':'test@example.com'},
                    headers={'Authorization':'Bearer '+token('hr')})
                self.assertEqual(allowed.status_code,503)
        self.assertEqual(TestClient(main.app).get('/api/live').status_code,200)

    def test_ready_requires_actual_db(self):
        with patch.object(main,'get_connection',side_effect=RuntimeError('offline')):
            response=TestClient(main.app).get('/api/ready')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['detail']['code'],'DATABASE_UNAVAILABLE')

    def test_overview_filters_exact_selected_nodes(self):
        import extended
        queries=[]
        fake_nodes=[{'employee_id':1,'full_name':'A','title':None,'department_id':1},
                    {'employee_id':3,'full_name':'B','title':None,'department_id':2}]
        fake_edges=[{'relation_type':'Knows','source_id':1,'target_id':3,'detail':'FRIEND'}]
        def fake_query(_,sql,binds):
            queries.append((sql,binds))
            return fake_nodes if 'SELECT employee_id,full_name,title' in sql else fake_edges
        # route endpoint function can be exercised directly through APIRouter
        router=extended.make_router(lambda f,write=False:f(object()))
        endpoint=next(route.endpoint for route in router.routes if route.path=='/api/graph/overview')
        with patch.object(extended,'query_all',side_effect=fake_query):
            result=endpoint(department_id=None,limit=2)
        self.assertEqual(len(result['edges']),1)
        self.assertFalse(result['truncated_edges'])
        self.assertIn('k.from_emp IN (:id0, :id1)',queries[1][0])
        self.assertNotIn('<= :maxid',queries[1][0])
        self.assertEqual(queries[1][1]['id0'],1)
        self.assertEqual(queries[1][1]['id1'],3)

    def test_migration_contains_no_drop(self):
        sql_dir=Path(__file__).resolve().parents[1]/'sql'/'setup'
        for script in ['MIGRATE_V4_TO_V5.sql','07_v5_teammate_sync.sql','08_reconcile_teammates.sql']:
            text=(sql_dir/script).read_text().upper()
            statements=[line.strip() for line in text.splitlines() if not line.lstrip().startswith('--')]
            self.assertFalse(any(line.startswith('DROP TABLE ') for line in statements))
        package=(sql_dir/'04_plsql.sql').read_text().upper()
        self.assertNotIn('    COMMIT;',package)
        self.assertNotIn('      ROLLBACK;',package)
        import inspect,graph_service,extended
        self.assertNotIn('connection.commit()',inspect.getsource(graph_service))
        self.assertNotIn('conn.commit()',inspect.getsource(extended))

if __name__=='__main__':unittest.main()
