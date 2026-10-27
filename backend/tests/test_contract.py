"""Database-free contract/unit smoke tests.

Run with `python -m unittest discover -s tests -v`. An installed python-oracledb
is preferred; a minimal stub is used only where the driver is unavailable.
These tests do not claim Oracle GRAPH_TABLE syntax was executed on a database.
"""
from __future__ import annotations

import importlib.util
import os
os.environ.update(ENVIRONMENT="test", ALLOW_TEST_AUTH_BYPASS="true", AUTH_MODE="test")
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if importlib.util.find_spec("oracledb") is None:
    fake = types.ModuleType("oracledb")
    fake.Error = type("Error", (Exception,), {})
    fake.LOB = type("LOB", (), {})
    fake.Connection = type("Connection", (), {})
    fake.ConnectionPool = type("ConnectionPool", (), {})
    fake.Cursor = type("Cursor", (), {})
    fake.enable_thin_mode = lambda: None
    fake.is_thin_mode = lambda: True
    sys.modules["oracledb"] = fake

from fastapi.testclient import TestClient
from pydantic import ValidationError

import graph_service
from main import app
from schemas import ConnectionCreate, ConnectionUpdate, ShortestPathRequest, ShortestPathResponse


class GraphContractsTest(unittest.TestCase):
    def test_static_sql_allowlist(self):
        self.assertEqual(sorted(graph_service.EMPLOYEE_STEP_SQL), [1, 2, 3, 4, 5, 6])
        for count, sql in graph_service.EMPLOYEE_STEP_SQL.items():
            self.assertIn("-{" + str(count) + "}", sql)
            self.assertIn("MATCHNUM()", sql)
            self.assertIn("ELEMENT_NUMBER(edge_step)", sql)
            self.assertIn(":src_id", sql)
            self.assertIn(":dst_id", sql)
        self.assertEqual(sorted(graph_service.MIXED_STEP_SQL), [1, 2, 3, 4, 5])
        self.assertEqual(sorted(graph_service.KHOPS_SQL), [1, 2, 3])

    def test_pydantic_constraints(self):
        with self.assertRaises(ValidationError):
            ShortestPathRequest(source_id=20, target_id=1, max_hops=7)
        with self.assertRaises(ValidationError):
            ConnectionCreate(from_emp=1, to_emp=2, strength=5.1)
        with self.assertRaises(ValidationError):
            ConnectionCreate(from_emp=1, to_emp=2, connection_type="UNKNOWN")
        self.assertEqual(ConnectionUpdate(from_emp=1, to_emp=2, notes=None).model_fields_set,
                         {"from_emp", "to_emp", "notes"})

    def test_bfs_finds_simple_two_hop_path(self):
        def step(match_no, no, source, target):
            return {
                "match_no": match_no, "element_no": no,
                "from": ("Employee", source, str(source), "Dev"),
                "to": ("Employee", target, str(target), "Dev"),
                "category": "Knows", "relation_type": "FRIEND", "strength": 2.0,
            }
        records = [step(1, 2, 20, 11), step(1, 4, 11, 1),
                   step(2, 2, 20, 15), step(2, 4, 15, 1)]
        candidates = graph_service._bfs_shortest_paths(records, ("Employee", 20), ("Employee", 1), 2)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0][0]["from"][1], 20)
        self.assertEqual(candidates[0][-1]["to"][1], 1)

    def test_shortest_json_contract(self):
        class FakeCursor:
            def __enter__(self): return self
            def __exit__(self, exc_type, exc_value, traceback): pass
            def callfunc(self, *args): return 2

        class FakeConnection:
            def cursor(self): return FakeCursor()

        rows = [
            {"match_no": 1, "element_no": 2, "from_employee_id": 20,
             "from_name": "Nhân viên 20", "from_title": "Junior", "to_employee_id": 11,
             "to_name": "Nhân viên 11", "to_title": "Senior",
             "relation_category": "Knows", "relation_type": "COLLEAGUE", "strength": 2.0},
            {"match_no": 1, "element_no": 4, "from_employee_id": 11,
             "from_name": "Nhân viên 11", "from_title": "Senior", "to_employee_id": 1,
             "to_name": "CEO", "to_title": "Director",
             "relation_category": "Knows", "relation_type": "FRIEND", "strength": 4.0},
        ]
        with patch.object(graph_service, "find_employee", return_value={"status": "ACTIVE"}), \
             patch.object(graph_service, "query_all", return_value=rows), \
             patch.object(graph_service, "query_one", return_value=None):
            result = graph_service.shortest_path(
                FakeConnection(), ShortestPathRequest(source_id=20, target_id=1)
            )
        validated = ShortestPathResponse.model_validate(result)
        self.assertTrue(validated.found)
        self.assertEqual(validated.path_length, 2)
        self.assertEqual(len(validated.elements.nodes), 3)
        self.assertEqual(len(validated.elements.edges), 2)
        self.assertEqual(validated.elements.edges[0].data["source"], "emp_20")
        self.assertEqual(validated.elements.edges[-1].data["target"], "emp_1")

    def test_route_paths_and_http_validation(self):
        client = TestClient(app)
        presets = client.get("/api/demo/presets")
        self.assertEqual(presets.status_code, 200)
        self.assertGreaterEqual(len(presets.json()), 5)
        self.assertEqual(client.post("/api/graph/shortest-path", json={
            "source_id": 20, "target_id": 1, "max_hops": 7,
        }).status_code, 422)
        self.assertEqual(client.get("/api/graph/khops/8?k=4").status_code, 422)
        schema = client.get("/openapi.json")
        self.assertEqual(schema.status_code, 200)
        paths = schema.json()["paths"]
        for route in (
            "/api/employees", "/api/employees/{emp_id}/profile",
            "/api/graph/shortest-path", "/api/graph/subordinates/{manager_id}",
            "/api/graph/teammates/{emp_id}", "/api/graph/check-teammate",
            "/api/graph/khops/{emp_id}", "/api/connections",
            "/api/projects/{project_id}/members", "/api/stats", "/api/audit-logs",
        ):
            self.assertIn(route, paths)


if __name__ == "__main__":
    unittest.main()
