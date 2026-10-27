"""V7 security/privacy unit tests: offline DB is intentionally unavailable."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_contract  # stub only when oracle driver is not installed; test-only auth bypass
import jwt
import main
import security
from fastapi.testclient import TestClient

SECRET = 'test-secret-more-than-thirty-two-characters-really'

def token(role='employee', subject='demo'):
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub': subject, 'roles': [role], 'iat':now,
        'exp':now + timedelta(minutes=30), 'iss':'linko-local', 'aud':'linko-api'}, SECRET,algorithm='HS256')

class V7Security(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_fail_closed_without_secret_even_if_test_settings_set(self):
        with patch.dict(os.environ, {'AUTH_MODE':'local', 'JWT_SECRET':''}):
            r = self.client.get('/api/employees')
            self.assertEqual(r.status_code,503)
            self.assertEqual(r.json()['detail']['code'],'AUTH_CONFIG_ERROR')

    def test_test_bypass_forbidden_in_production(self):
        with patch.dict(os.environ, {'AUTH_MODE':'test', 'ENVIRONMENT':'production'}):
            r = self.client.get('/api/employees')
            self.assertEqual(r.status_code,503)

    def test_expired_token_denied_and_read_post_requires_only_employee(self):
        now=datetime.now(timezone.utc)
        expired=jwt.encode({'sub':'eve','roles':['admin'],'iss':'linko-local','aud':'linko-api',
                            'iat':now-timedelta(days=2),'exp':now-timedelta(days=1)},
                            SECRET,algorithm='HS256')
        with patch.dict(os.environ, {'AUTH_MODE':'local','JWT_SECRET':SECRET}):
            self.assertEqual(self.client.get('/api/employees',headers={'Authorization':'Bearer '+expired}).status_code,401)
            with patch.object(main,'get_connection',side_effect=RuntimeError('offline')):
                r=self.client.post('/api/graph/shortest-path',json={'source_id':1,'target_id':3},
                    headers={'Authorization':'Bearer '+token('employee')})
            self.assertEqual(r.status_code,503)
            self.assertEqual(r.json()['detail']['code'],'DATABASE_UNAVAILABLE')

    def test_role_matrix(self):
        with patch.dict(os.environ, {'AUTH_MODE':'local','JWT_SECRET':SECRET}):
            emp={'Authorization':'Bearer '+token('employee')}
            hr={'Authorization':'Bearer '+token('hr')}
            for method, route, headers, status in [
                ('delete','/api/employees/3',emp,403),
                ('delete','/api/employees/3',hr,403),
                ('get','/api/audit-logs',emp,403),
                ('get','/api/data/employees/3/delete-impact',emp,403),
                ('post','/api/employees',emp,403),
            ]:
                with self.subTest(method=method,route=route):
                    r = self.client.request(method,route,headers=headers)
                    self.assertEqual(r.status_code,status)
            self.assertEqual(self.client.get('/api/live').status_code,200)

    def test_openapi_has_bearer_scheme(self):
        spec=self.client.get('/openapi.json').json()
        self.assertIn('BearerAuth',spec['components']['securitySchemes'])
        self.assertEqual(spec['paths']['/api/employees']['get']['security'],[{'BearerAuth':[]}])

    def test_sql_migration_is_additive_and_audits_all_business_tables(self):
        path=Path(__file__).resolve().parents[1]/'sql'/'setup'/'09_v7_full_audit.sql'
        sql=path.read_text().upper()
        for table in ['EMPLOYEES','DEPARTMENTS','PROJECTS','PROJECT_MEMBERS','REPORTS_TO','KNOWS']:
            self.assertIn(f"('{table}'",sql)
        self.assertNotIn('DROP TABLE',sql)
        self.assertIn('CLIENT_IDENTIFIER',sql)

    def test_graph_step_sql_contains_intermediate_status(self):
        import graph_service
        for sql in [graph_service.EMPLOYEE_STEP_SQL[1],graph_service.MIXED_STEP_SQL[2]]:
            self.assertIn('v1.status AS from_status',sql)
            self.assertIn('v2.status AS to_status',sql)
        rows=[{'from_employee_id':1,'to_employee_id':2,'from_status':'ACTIVE',
               'to_status':'INACTIVE', 'match_no':1, 'element_no':1}]
        self.assertEqual(graph_service._normalize_graph_steps(rows,False),[])

if __name__=='__main__': unittest.main()
