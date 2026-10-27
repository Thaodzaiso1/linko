"""Extended endpoints: OpenAPI and validation only; no Oracle instance needed."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_contract
from fastapi.testclient import TestClient
from main import app
from extended import EmployeeCreate, ProjectCreate
from pydantic import ValidationError

class ExtendedContractTest(unittest.TestCase):
    def test_routes_exposed(self):
        paths=TestClient(app).get('/openapi.json').json()['paths']
        expected=['/api/employees/{employee_id}', '/api/departments/{department_id}',
                  '/api/projects/{project_id}', '/api/projects/{project_id}/members',
                  '/api/projects/{project_id}/members/{employee_id}',
                  '/api/employees/{employee_id}/manager', '/api/graph/overview',
                  '/api/stats/departments', '/api/stats/top-connectors', '/api/connections']
        for path in expected:
            with self.subTest(path=path): self.assertIn(path,paths)
        self.assertIn('patch',paths['/api/employees/{employee_id}'])

    def test_invalid_payloads(self):
        with self.assertRaises(ValidationError):EmployeeCreate(full_name='',email='bad')
        with self.assertRaises(ValidationError):ProjectCreate(project_name='X',status='UNKNOWN')
        client=TestClient(app)
        self.assertEqual(client.post('/api/employees',json={'full_name':'A','email':'bad'}).status_code,422)
        self.assertEqual(client.get('/api/graph/overview?limit=900').status_code,422)
