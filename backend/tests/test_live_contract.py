"""Offline guards for the real-DB-only runtime. No fake HTTP graph results."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
# The existing test_contract module installs a test-only driver shim in this
# environment when the optional external package is absent.
import test_contract
import main
from fastapi.testclient import TestClient
from schemas import ConnectionCreate

class LiveContractTest(unittest.TestCase):
    def test_live_not_same_as_readiness(self):
        client=TestClient(main.app)
        self.assertEqual(client.get('/api/live').json()['database'],'not_checked')
        with patch.object(main,'get_connection',side_effect=RuntimeError('no connection')):
            response=client.get('/api/health')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['detail']['code'],'DATABASE_UNAVAILABLE')

    def test_v7_routes_and_v3_kept(self):
        routes=TestClient(main.app).get('/openapi.json').json()['paths']
        for r in ['/api/paths/shortest','/api/graph/shortest-path',
                  '/api/departments/stats','/api/dashboard/overview',
                  '/api/org/summary','/api/stats/overview',
                  '/api/employees/{employee_id}/connections']:
            with self.subTest(route=r):self.assertIn(r,routes)
        obj=ConnectionCreate(from_id=1,to_id=2)
        self.assertEqual((obj.from_emp,obj.to_emp),(1,2))

    def test_mutations_never_go_through_fake_db(self):
        client=TestClient(main.app)
        with patch.object(main,'get_connection',side_effect=RuntimeError('no Oracle DB')):
            reply=client.post('/api/employees',json={'full_name':'Testing','email':'test@example.org'})
        self.assertEqual(reply.status_code,503)
        self.assertEqual(reply.json()['detail']['code'],'DATABASE_UNAVAILABLE')

if __name__=='__main__': unittest.main()
