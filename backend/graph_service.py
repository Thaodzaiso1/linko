"""SQL Property Graph / PL-SQL application service for Oracle Database 23ai.

Prerequisite: Oracle Database 23ai Release Update 23.8+ for MATCHNUM() and
ELEMENT_NUMBER() in ONE ROW PER STEP queries.

No SQL identifier or value is assembled from user-supplied text. Graph path
quantifiers cannot be bound, so every allowed fixed hop count is precompiled
into an immutable, allow-listed SQL statement at module import.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict, deque
from typing import Any, Iterable

import oracledb

from database import call_refcursor, query_all, query_one, scalar
from exceptions import api_error, require_found
from schemas import ConnectionCreate, ConnectionDelete, ConnectionUpdate, ProjectMemberCreate, ShortestPathRequest

logger = logging.getLogger(__name__)
MAX_GRAPH_RESULT_ROWS = 30001
MAX_GRAPH_NODES = 500

# MATCHNUM + ELEMENT_NUMBER ensure that steps can also be reconstructed as
# complete individual Oracle path matches (rather than interleaved rows).
_EMPLOYEE_PATH_TEMPLATE = """
SELECT match_no, element_no,
       from_employee_id, from_name, from_title,
       to_employee_id, to_name, to_title,
       relation_category, relation_type, strength, from_status, to_status
FROM GRAPH_TABLE (
    enterprise_social_graph
    MATCH (
        (src IS Employee WHERE src.employee_id = :src_id)
        -[edge IS Knows|ReportsTo]-__REPETITION__
        (dst IS Employee WHERE dst.employee_id = :dst_id)
    )
    ONE ROW PER STEP (v1, edge_step, v2)
    COLUMNS (
        MATCHNUM() AS match_no,
        ELEMENT_NUMBER(edge_step) AS element_no,
        v1.employee_id AS from_employee_id,
        v1.full_name AS from_name,
        v1.title AS from_title,
        v1.status AS from_status,
        v2.status AS to_status,
        v2.employee_id AS to_employee_id,
        v2.full_name AS to_name,
        v2.title AS to_title,
        CASE WHEN edge_step.connection_type IS NOT NULL
             THEN 'Knows' ELSE 'ReportsTo' END AS relation_category,
        edge_step.connection_type AS relation_type,
        edge_step.strength AS strength
    )
)
ORDER BY match_no, element_no
FETCH FIRST :max_rows ROWS ONLY
"""

_MIXED_PATH_TEMPLATE = """
SELECT match_no, element_no,
       from_employee_id, from_project_id, from_name, from_title,
       to_employee_id, to_project_id, to_name, to_title,
       relation_category, relation_type, strength, from_status, to_status
FROM GRAPH_TABLE (
    enterprise_social_graph
    MATCH (
        (src IS Employee WHERE src.employee_id = :src_id)
        -[edge IS Knows|ReportsTo|WorksOn]-__REPETITION__
        (dst IS Employee WHERE dst.employee_id = :dst_id)
    )
    ONE ROW PER STEP (v1, edge_step, v2)
    COLUMNS (
        MATCHNUM() AS match_no,
        ELEMENT_NUMBER(edge_step) AS element_no,
        v1.employee_id AS from_employee_id,
        v1.project_id AS from_project_id,
        COALESCE(v1.full_name, v1.project_name) AS from_name,
        v1.title AS from_title,
        v1.status AS from_status,
        v2.status AS to_status,
        v2.employee_id AS to_employee_id,
        v2.project_id AS to_project_id,
        COALESCE(v2.full_name, v2.project_name) AS to_name,
        v2.title AS to_title,
        CASE WHEN v1.project_id IS NOT NULL OR v2.project_id IS NOT NULL
             THEN 'WorksOn'
             WHEN edge_step.connection_type IS NOT NULL
             THEN 'Knows' ELSE 'ReportsTo' END AS relation_category,
        edge_step.connection_type AS relation_type,
        edge_step.strength AS strength
    )
)
ORDER BY match_no, element_no
FETCH FIRST :max_rows ROWS ONLY
"""

# The replacement values below come exclusively from hard-coded integers,
# not interpolated HTTP parameters. IDs remain :src_id / :dst_id binds.
EMPLOYEE_STEP_SQL: dict[int, str] = {
    hops: _EMPLOYEE_PATH_TEMPLATE.replace("__REPETITION__", "{" + str(hops) + "}")
    for hops in (1, 2, 3, 4, 5, 6)
}
MIXED_STEP_SQL: dict[int, str] = {
    hops: _MIXED_PATH_TEMPLATE.replace("__REPETITION__", "{" + str(hops) + "}")
    for hops in (1, 2, 3, 4, 5)
}

# Constant, independent query for comparing 2..5-hop paths containing Project nodes.
MIXED_MIN_LENGTH_SQL = """
SELECT MIN(path_length) AS path_length FROM GRAPH_TABLE (
    enterprise_social_graph
    MATCH (
        (a IS Employee WHERE a.employee_id = :src_id)
        -[edge IS Knows|ReportsTo|WorksOn]-{1,5}
        (b IS Employee WHERE b.employee_id = :dst_id)
    )
    COLUMNS (COUNT(edge) AS path_length)
)
"""

SUBORDINATES_SQL = """
SELECT emp_id AS employee_id, full_name, title, MIN(level_num) AS level_num
FROM GRAPH_TABLE (
    enterprise_social_graph
    MATCH (manager IS Employee WHERE manager.employee_id = :manager_id)
          <-[r IS ReportsTo]-{1,5} (child IS Employee)
    COLUMNS (child.employee_id AS emp_id, child.full_name AS full_name,
             child.title AS title, COUNT(r) AS level_num)
)
GROUP BY emp_id, full_name, title
ORDER BY level_num, full_name
"""

TEAMMATES_GRAPH_SQL = """
SELECT DISTINCT me_id, me_name, proj_id, proj_name,
       tm_id, tm_name, tm_title, me_role, tm_role
FROM GRAPH_TABLE (
    enterprise_social_graph
    MATCH (me IS Employee WHERE me.employee_id = :emp_id)
          -[w1 IS WorksOn]-> (project IS Project)
          <-[w2 IS WorksOn]- (teammate IS Employee)
    WHERE teammate.employee_id <> :emp_id
    COLUMNS (
        me.employee_id AS me_id, me.full_name AS me_name,
        project.project_id AS proj_id, project.project_name AS proj_name,
        teammate.employee_id AS tm_id, teammate.full_name AS tm_name,
        teammate.title AS tm_title,
        w1.role AS me_role, w2.role AS tm_role
    )
)
ORDER BY proj_name, tm_name
"""

_KHOPS_TEMPLATE = """
SELECT reached_id AS employee_id, full_name, title, MIN(hops) AS hops
FROM GRAPH_TABLE (
    enterprise_social_graph
    MATCH (start_emp IS Employee WHERE start_emp.employee_id = :emp_id)
          -[k_edge IS Knows]-__REPETITION__ (reached IS Employee)
    WHERE reached.employee_id <> :emp_id AND reached.status = 'ACTIVE'
    COLUMNS (reached.employee_id AS reached_id,
             reached.full_name AS full_name, reached.title AS title,
             COUNT(k_edge) AS hops)
)
GROUP BY reached_id, full_name, title
ORDER BY hops, full_name
"""
KHOPS_SQL: dict[int, str] = {
    hops: _KHOPS_TEMPLATE.replace("__REPETITION__", "{1," + str(hops) + "}")
    for hops in (1, 2, 3)
}


def find_employee(connection: oracledb.Connection, emp_id: int, active: bool = False) -> dict[str, Any]:
    row = query_one(
        connection,
        """
        SELECT e.employee_id, e.full_name, e.email, e.title, e.department_id,
               e.hire_date, e.phone, e.status, e.created_at,
               d.department_name, d.location, r.manager_id, m.full_name AS manager_name
        FROM employees e
        LEFT JOIN departments d ON d.department_id = e.department_id
        LEFT JOIN reports_to r ON r.employee_id = e.employee_id
        LEFT JOIN employees m ON m.employee_id = r.manager_id
        WHERE e.employee_id = :emp_id
        """,
        {"emp_id": emp_id},
    )
    if row is None or (active and row["status"] != "ACTIVE"):
        raise api_error(404, "EMPLOYEE_NOT_FOUND", "Nhân viên không tồn tại hoặc không ở trạng thái ACTIVE.")
    return row


def find_employees(
    connection: oracledb.Connection,
    q: str | None,
    department_id: int | None,
    status: str,
    limit: int,
) -> list[dict[str, Any]]:
    needle = (q or "").strip().lower()
    # Escape SQL LIKE wildcards; case-insensitive and input is always bound.
    escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return query_all(
        connection,
        """
        SELECT e.employee_id, e.full_name, e.email, e.title, e.status,
               e.department_id, d.department_name, r.manager_id,
               m.full_name AS manager_name
        FROM employees e
        LEFT JOIN departments d ON d.department_id = e.department_id
        LEFT JOIN reports_to r ON r.employee_id = e.employee_id
        LEFT JOIN employees m ON m.employee_id = r.manager_id
        WHERE (:status = 'ALL' OR e.status = :status)
          AND (:department_id IS NULL OR e.department_id = :department_id)
          AND (:search_disabled = 1 OR LOWER(e.full_name) LIKE :pattern ESCAPE '\\'
                OR LOWER(e.email) LIKE :pattern ESCAPE '\\'
                OR LOWER(e.title) LIKE :pattern ESCAPE '\\')
        ORDER BY e.full_name, e.employee_id
        FETCH FIRST :row_limit ROWS ONLY
        """,
        {
            "status": status,
            "department_id": department_id,
            "search_disabled": int(not bool(needle)),
            "pattern": "%" + escaped + "%",
            "row_limit": limit,
        },
    )


def department_list(connection: oracledb.Connection) -> list[dict[str, Any]]:
    return query_all(connection, """
        SELECT d.department_id, d.department_name, d.location,
               COUNT(e.employee_id) AS employee_count,
               SUM(CASE WHEN e.status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_count
        FROM departments d LEFT JOIN employees e ON e.department_id = d.department_id
        GROUP BY d.department_id, d.department_name, d.location
        ORDER BY d.department_id
    """)


def project_list(connection: oracledb.Connection) -> list[dict[str, Any]]:
    return query_all(connection, """
        SELECT p.project_id, p.project_name, p.description, p.start_date,
               p.end_date, p.status, p.department_id,
               d.department_name, COUNT(pm.employee_id) AS member_count
        FROM projects p
        LEFT JOIN departments d ON d.department_id = p.department_id
        LEFT JOIN project_members pm ON pm.project_id = p.project_id
        GROUP BY p.project_id, p.project_name, p.description, p.start_date,
                 p.end_date, p.status, p.department_id, d.department_name
        ORDER BY p.project_id
    """)


def teammate_cursor(connection: oracledb.Connection, emp_id: int) -> list[dict[str, Any]]:
    return call_refcursor(connection, "pkg_social_network.get_teammates", emp_id)


def network_counts(raw_stats: str | None) -> dict[str, int]:
    pattern = re.compile(r"Outgoing:\s*(\d+)\s*\|\s*Incoming:\s*(\d+)\s*\|\s*Projects:\s*(\d+)")
    match = pattern.fullmatch((raw_stats or "").strip())
    if not match:
        raise api_error(500, "STATS_PARSE_ERROR", "Package trả về định dạng thống kê không hợp lệ.")
    return {"outgoing": int(match[1]), "incoming": int(match[2]), "projects": int(match[3])}


def employee_profile(connection: oracledb.Connection, emp_id: int) -> dict[str, Any]:
    employee = find_employee(connection, emp_id)
    with connection.cursor() as cursor:
        raw = cursor.callfunc("pkg_social_network.get_network_stats", str, [emp_id])
    projects = query_all(connection, """
        SELECT p.project_id, p.project_name, p.status, pm.role, pm.join_date
        FROM project_members pm JOIN projects p ON p.project_id = pm.project_id
        WHERE pm.employee_id = :emp_id
        ORDER BY p.project_name
    """, {"emp_id": emp_id})
    manager = None
    if employee["manager_id"] is not None:
        manager = query_one(connection, """
            SELECT e.employee_id, e.full_name, e.title, e.status
            FROM employees e WHERE e.employee_id = :manager_id
        """, {"manager_id": employee["manager_id"]})
    direct_reports = query_all(connection, """
        SELECT e.employee_id, e.full_name, e.title, e.status
        FROM reports_to r JOIN employees e ON e.employee_id = r.employee_id
        WHERE r.manager_id = :emp_id ORDER BY e.full_name
    """, {"emp_id": emp_id})
    socials = query_all(connection, """
        SELECT k.from_emp, k.to_emp, k.connection_type, k.strength, k.since_date,
               e.employee_id, e.full_name, e.title, e.status,
               CASE WHEN k.from_emp = :emp_id THEN 'outgoing' ELSE 'incoming' END AS direction
        FROM knows k JOIN employees e
          ON e.employee_id = CASE WHEN k.from_emp = :emp_id THEN k.to_emp ELSE k.from_emp END
        WHERE k.from_emp = :emp_id OR k.to_emp = :emp_id
        ORDER BY e.full_name, direction
    """, {"emp_id": emp_id})
    return {
        "employee": employee,
        "network_stats": network_counts(raw),
        "projects": projects,
        "manager": manager,
        "direct_reports": direct_reports,
        "teammates": teammate_cursor(connection, emp_id),
        "social_connections": socials,
    }


def _node_key(label: str, identity: int) -> str:
    return ("proj_" if label == "Project" else "emp_") + str(identity)


def _node(label: str, identity: int, name: str, title: str | None = None,
          role: str | None = None) -> dict[str, Any]:
    return {"data": {
        "id": _node_key(label, identity), "raw_id": identity, "label": name,
        "title": title, "type": label, "role_in_path": role,
        "color": "#16a34a" if label == "Project" else "#2563eb",
        "shape": "round-rectangle" if label == "Project" else "ellipse",
    }}


def _empty_path(body: ShortestPathRequest) -> dict[str, Any]:
    return {
        "found": False,
        "source_id": body.source_id,
        "target_id": body.target_id,
        "max_hops": body.max_hops,
        "include_projects": body.include_projects,
        "path_length": None,
        "message": "Không tìm thấy đường kết nối giữa 2 nhân viên này.",
        "steps": [],
        "elements": {"nodes": [], "edges": []},
        "alternative_paths": [],
    }


def _vertex(record: dict[str, Any], prefix: str) -> tuple[str, int, str, str | None]:
    project_id = record.get(prefix + "_project_id")
    employee_id = record.get(prefix + "_employee_id")
    if project_id is not None:
        return "Project", int(project_id), str(record[prefix + "_name"]), None
    if employee_id is None:
        raise api_error(500, "GRAPH_RESULT_ERROR", "Oracle trả về một đỉnh không có khóa.")
    return "Employee", int(employee_id), str(record[prefix + "_name"]), record.get(prefix + "_title")


def _normalize_graph_steps(rows: list[dict[str, Any]], include_projects: bool) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        # Reject walks that cross a non-active Employee (including intermediate
        # vertices). Project status is independent of Employee activity.
        if ((row.get('from_employee_id') is not None and row.get('from_status', 'ACTIVE') != 'ACTIVE')
                or (row.get('to_employee_id') is not None and row.get('to_status', 'ACTIVE') != 'ACTIVE')):
            continue
        if include_projects:
            source = _vertex(row, "from")
            target = _vertex(row, "to")
        else:
            source = ("Employee", int(row["from_employee_id"]), str(row["from_name"]), row.get("from_title"))
            target = ("Employee", int(row["to_employee_id"]), str(row["to_name"]), row.get("to_title"))
        result.append({
            "match_no": int(row["match_no"]),
            "element_no": int(row["element_no"]),
            "from": source,
            "to": target,
            "category": str(row["relation_category"]),
            "relation_type": row.get("relation_type"),
            "strength": row.get("strength"),
        })
    return result


def _bfs_shortest_paths(
    graph_edges: list[dict[str, Any]], source: tuple[str, int],
    target: tuple[str, int], desired_length: int, limit: int = 3,
) -> list[list[dict[str, Any]]]:
    """BFS over actual GRAPH_TABLE step adjacencies; never mixes unrelated IDs.

    Undirected patterns walk edges in either direction. Keeping a path-local
    visited set ensures simple paths, while limiting depth caps combinatorics.
    """
    adjacency: dict[tuple[str, int], dict[tuple[str, int], dict[str, Any]]] = defaultdict(dict)
    for record in graph_edges:
        u = (record["from"][0], record["from"][1])
        v = (record["to"][0], record["to"][1])
        if u != v:
            adjacency[u].setdefault(v, record)
    # Reverse breadth-first distances prune branches that cannot reach target
    # in the exact remaining number of hops.
    reverse_adj: dict[tuple[str, int], set[tuple[str, int]]] = defaultdict(set)
    for vertex, neighbors in adjacency.items():
        for neighbor in neighbors:
            reverse_adj[neighbor].add(vertex)
    distance: dict[tuple[str, int], int] = {target: 0}
    to_visit = deque([target])
    while to_visit:
        current = to_visit.popleft()
        for previous in reverse_adj.get(current, set()):
            if previous not in distance:
                distance[previous] = distance[current] + 1
                to_visit.append(previous)
    queue = deque([(source, [source], [])])
    found: list[list[dict[str, Any]]] = []
    seen_paths: set[tuple[tuple[str, int], ...]] = set()
    traversed = 0
    while queue and len(found) < limit:
        node, seen, steps = queue.popleft()
        if len(steps) == desired_length:
            if node == target and tuple(seen) not in seen_paths:
                found.append(steps)
                seen_paths.add(tuple(seen))
            continue
        if node == target:
            continue
        for next_node, step in sorted(adjacency.get(node, {}).items()):
            if next_node in seen:
                continue
            remaining = desired_length - len(steps) - 1
            if next_node not in distance or distance[next_node] > remaining:
                continue
            queue.append((next_node, seen + [next_node], steps + [step]))
            traversed += 1
            if traversed > 150000:
                raise api_error(422, "PATH_SEARCH_TOO_LARGE", "Mạng quá dày để dựng đường đi với giới hạn hiện tại.")
    return found


def _exact_matches(graph_edges: list[dict[str, Any]], source: tuple[str, int],
                   target: tuple[str, int], length: int) -> list[list[dict[str, Any]]]:
    by_match: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in graph_edges:
        by_match[row["match_no"]].append(row)
    paths = []
    for rows in by_match.values():
        ordered = sorted(rows, key=lambda entry: entry["element_no"])
        if (len(ordered) == length
                and (ordered[0]["from"][0], ordered[0]["from"][1]) == source
                and (ordered[-1]["to"][0], ordered[-1]["to"][1]) == target
                and all(ordered[index]["to"][:2] == ordered[index + 1]["from"][:2]
                        for index in range(len(ordered) - 1))):
            paths.append(ordered)
            if len(paths) >= 3:
                break
    return paths


def _enrich_step(connection: oracledb.Connection, record: dict[str, Any]) -> dict[str, Any]:
    left, right = record["from"], record["to"]
    category = record["category"]
    result: dict[str, Any] = {
        "category": category,
        "detail": category,
        "direction": f"{_node_key(left[0], left[1])}->{_node_key(right[0], right[1])}",
        "strength": float(record["strength"]) if record["strength"] is not None else None,
    }
    if category == "ReportsTo":
        relation = query_one(connection, """
            SELECT employee_id, manager_id FROM reports_to
            WHERE (employee_id = :a AND manager_id = :b)
               OR (employee_id = :b AND manager_id = :a)
        """, {"a": left[1], "b": right[1]})
        if relation:
            result["direction"] = f"{relation['employee_id']}->{relation['manager_id']}"
            result["detail"] = "Báo cáo trực tiếp (nhân viên → quản lý)"
    elif category == "Knows":
        relation = query_one(connection, """
            SELECT from_emp, to_emp, connection_type, strength FROM knows
            WHERE ((from_emp = :a AND to_emp = :b)
                OR (from_emp = :b AND to_emp = :a))
              AND (:relation_type IS NULL OR connection_type = :relation_type)
            ORDER BY CASE WHEN from_emp = :a AND to_emp = :b THEN 0 ELSE 1 END
            FETCH FIRST 1 ROW ONLY
        """, {"a": left[1], "b": right[1],
               "relation_type": record.get("relation_type")})
        if relation:
            result["direction"] = f"{relation['from_emp']}->{relation['to_emp']}"
            result["detail"] = str(relation["connection_type"])
            result["strength"] = float(relation["strength"]) if relation["strength"] is not None else None
    elif category == "WorksOn":
        if left[0] == "Employee":
            emp_id, proj_id = left[1], right[1]
        else:
            emp_id, proj_id = right[1], left[1]
        relation = query_one(connection, """
            SELECT employee_id, project_id, role FROM project_members
            WHERE employee_id = :emp_id AND project_id = :proj_id
        """, {"emp_id": emp_id, "proj_id": proj_id})
        if relation:
            result["detail"] = "Tham gia dự án: " + str(relation["role"] or "MEMBER")
            result["direction"] = f"emp_{emp_id}->proj_{proj_id}"
    return result


def _path_as_response(connection: oracledb.Connection, path: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    for index, record in enumerate(path, 1):
        left, right = record["from"], record["to"]
        for vertex in (left, right):
            identity = _node_key(vertex[0], vertex[1])
            nodes.setdefault(identity, _node(vertex[0], vertex[1], vertex[2], vertex[3]))
        metadata = _enrich_step(connection, record)
        steps.append({
            "step": index,
            "from_id": left[1], "from_name": left[2], "to_id": right[1], "to_name": right[2],
            "from_type": left[0], "to_type": right[0],
            "relation_category": metadata["category"],
            "relation_detail": metadata["detail"],
            "direction": metadata["direction"],
            "strength": metadata["strength"],
        })
        edges.append({"data": {
            "id": f"path_edge_{index}_{_node_key(left[0], left[1])}_{_node_key(right[0], right[1])}",
            "source": _node_key(left[0], left[1]),
            "target": _node_key(right[0], right[1]),
            "label": metadata["detail"],
            "category": metadata["category"],
            "strength": metadata["strength"],
            "direction": metadata["direction"],
        }})
    if path:
        nodes[_node_key(path[0]["from"][0], path[0]["from"][1])]["data"]["role_in_path"] = "source"
        nodes[_node_key(path[-1]["to"][0], path[-1]["to"][1])]["data"]["role_in_path"] = "target"
    return {"steps": steps, "elements": {"nodes": list(nodes.values()), "edges": edges}}


def shortest_path(connection: oracledb.Connection, body: ShortestPathRequest) -> dict[str, Any]:
    if body.source_id == body.target_id:
        raise api_error(400, "SELF_CONNECTION", "Không thể tìm đường kết nối với chính mình.")
    find_employee(connection, body.source_id, active=True)
    find_employee(connection, body.target_id, active=True)

    if body.include_projects:
        # Oracle query Q5 is explicitly capped at five hops.
        effective_max = min(body.max_hops, 5)
        path_length = scalar(connection, MIXED_MIN_LENGTH_SQL,
                             {"src_id": body.source_id, "dst_id": body.target_id})
    else:
        with connection.cursor() as cursor:
            path_length = cursor.callfunc(
                "pkg_social_network.find_shortest_path_length", int,
                [body.source_id, body.target_id, body.max_hops],
            )
        effective_max = body.max_hops

    # The currently provided 04_plsql.sql uses {1,6} even if p_max_hops<6.
    # Enforce the actual API cap before requesting step details.
    if path_length is None or int(path_length) > effective_max:
        return _empty_path(body)
    path_length = int(path_length)
    if path_length < 1:
        raise api_error(500, "INVALID_PATH_LENGTH", "Độ dài đường đi Oracle trả về không hợp lệ.")
    sql_map = MIXED_STEP_SQL if body.include_projects else EMPLOYEE_STEP_SQL
    source = ("Employee", body.source_id)
    target = ("Employee", body.target_id)
    # The original PL/SQL reports the minimum WITHOUT checking intermediate
    # status. Progressively test exact lengths until a valid ACTIVE-only path
    # is found. Never return a longer path as though it were globally shortest
    # when a shorter ACTIVE path is available.
    candidates = []
    for exact_length in range(path_length, effective_max + 1):
        rows = query_all(connection, sql_map[exact_length], {
            "src_id": body.source_id,
            "dst_id": body.target_id,
            "max_rows": MAX_GRAPH_RESULT_ROWS,
        })
        if len(rows) >= MAX_GRAPH_RESULT_ROWS:
            raise api_error(422, "GRAPH_RESULT_TOO_LARGE",
                            "Quá nhiều walk; không thể xác nhận đường ngắn nhất chính xác.")
        records = _normalize_graph_steps(rows, body.include_projects)
        candidates = _exact_matches(records, source, target, exact_length)
        if not candidates:
            candidates = _bfs_shortest_paths(records, source, target, exact_length)
        if candidates:
            path_length = exact_length
            break
    if not candidates:
        return _empty_path(body)
    rendered = _path_as_response(connection, candidates[0])
    alternatives = []
    for candidate in candidates[1:3]:
        alternatives.append({
            "node_ids": [_node_key(step["from"][0], step["from"][1]) for step in candidate]
                        + [_node_key(candidate[-1]["to"][0], candidate[-1]["to"][1])],
            "path_length": len(candidate),
        })
    return {
        "found": True,
        "source_id": body.source_id,
        "target_id": body.target_id,
        "max_hops": body.max_hops,
        "include_projects": body.include_projects,
        "path_length": path_length,
        "message": "Đã tìm thấy đường kết nối ngắn nhất.",
        "steps": rendered["steps"], "elements": rendered["elements"],
        "alternative_paths": alternatives,
    }


def subordinates(connection: oracledb.Connection, manager_id: int) -> dict[str, Any]:
    root = find_employee(connection, manager_id)
    graph_rows = query_all(connection, SUBORDINATES_SQL, {"manager_id": manager_id})
    hierarchy_rows = call_refcursor(connection, "sp_get_org_tree", manager_id)
    graph_ids = {int(row["employee_id"]) for row in graph_rows}
    # CONNECT BY procedure is unbounded; compare only levels up to five.
    within_five = [row for row in hierarchy_rows if int(row["org_level"]) <= 5]
    sql_ids = {int(row["employee_id"]) for row in within_five}
    all_ids = graph_ids | {manager_id}
    nodes = [_node("Employee", manager_id, root["full_name"], root["title"], "source")]
    for row in graph_rows:
        nodes.append(_node("Employee", int(row["employee_id"]), row["full_name"], row["title"]))
    reports = query_all(connection, """
        SELECT r.employee_id, r.manager_id FROM reports_to r
        WHERE r.employee_id IN (
            SELECT employee_id FROM employees WHERE employee_id = :manager_id
               OR employee_id IN (
                 SELECT child_id FROM GRAPH_TABLE (
                    enterprise_social_graph
                    MATCH (m IS Employee WHERE m.employee_id = :manager_id)
                          <-[edge IS ReportsTo]-{1,5} (ch IS Employee)
                    COLUMNS (ch.employee_id AS child_id)
                 )
               )
        )
    """, {"manager_id": manager_id})
    edges = [{"data": {
        "id": f"reports_{row['employee_id']}_{row['manager_id']}",
        "source": f"emp_{row['employee_id']}", "target": f"emp_{row['manager_id']}",
        "label": "ReportsTo", "category": "ReportsTo",
    }} for row in reports if row["employee_id"] in all_ids and row["manager_id"] in all_ids]
    return {
        "manager_id": manager_id,
        "graph_table": graph_rows, "connect_by": hierarchy_rows,
        "comparison": {
            "depth_compared": 5,
            "matching": graph_ids == sql_ids,
            "only_in_graph": sorted(graph_ids - sql_ids),
            "only_in_connect_by": sorted(sql_ids - graph_ids),
            "graph_count": len(graph_ids),
            "connect_by_within_five_count": len(sql_ids),
        },
        "elements": {"nodes": nodes, "edges": edges},
    }


def teammates_graph(connection: oracledb.Connection, emp_id: int) -> dict[str, Any]:
    me = find_employee(connection, emp_id)
    rows = query_all(connection, TEAMMATES_GRAPH_SQL, {"emp_id": emp_id})
    nodes = {f"emp_{emp_id}": _node("Employee", emp_id, me["full_name"], me["title"], "source")}
    edges: dict[str, dict[str, Any]] = {}
    for row in rows:
        proj = int(row["proj_id"])
        tm = int(row["tm_id"])
        nodes.setdefault(f"proj_{proj}", _node("Project", proj, row["proj_name"]))
        nodes.setdefault(f"emp_{tm}", _node("Employee", tm, row["tm_name"], row["tm_title"]))
        for member, role in ((emp_id, row["me_role"]), (tm, row["tm_role"])):
            eid = f"works_{member}_{proj}"
            edges[eid] = {"data": {
                "id": eid, "source": f"emp_{member}", "target": f"proj_{proj}",
                "category": "WorksOn", "label": str(role or "MEMBER"),
            }}
    return {"data": rows, "elements": {"nodes": list(nodes.values()), "edges": list(edges.values())}}


def check_teammate(connection: oracledb.Connection, emp1: int, emp2: int) -> dict[str, Any]:
    find_employee(connection, emp1)
    find_employee(connection, emp2)
    with connection.cursor() as cursor:
        result = cursor.callfunc("fn_is_teammate", str, [emp1, emp2])
    if result not in {"YES", "NO"}:
        raise api_error(500, "TEAMMATE_CHECK_ERROR", "Hàm fn_is_teammate trả về lỗi.")
    return {"emp1": emp1, "emp2": emp2, "is_teammate": result == "YES", "result": result}


def khops_graph(connection: oracledb.Connection, emp_id: int, k: int) -> dict[str, Any]:
    person = find_employee(connection, emp_id, active=True)
    rows = query_all(connection, KHOPS_SQL[k], {"emp_id": emp_id})
    if len(rows) > MAX_GRAPH_NODES:
        raise api_error(422, "GRAPH_TOO_LARGE", "Mạng vượt giới hạn 500 nhân viên được hiển thị.")
    node_ids = {emp_id} | {int(row["employee_id"]) for row in rows}
    nodes = [_node("Employee", emp_id, person["full_name"], person["title"], "source")]
    nodes += [_node("Employee", int(row["employee_id"]), row["full_name"], row["title"])
              for row in rows]

    # Bind every item; placeholder identifiers are generated from indexes,
    # never from HTTP strings. Avoids interpolating arbitrary ID values.
    parameters = {f"node_{index}": identity for index, identity in enumerate(sorted(node_ids))}
    placeholders = ", ".join(":" + name for name in parameters)
    sql = (
        "SELECT k.from_emp, k.to_emp, k.connection_type, k.strength "
        "FROM knows k WHERE k.from_emp IN (" + placeholders + ") "
        "AND k.to_emp IN (" + placeholders + ")"
    )
    connections = query_all(connection, sql, parameters)
    edges = [{"data": {
        "id": f"knows_{r['from_emp']}_{r['to_emp']}",
        "source": f"emp_{r['from_emp']}", "target": f"emp_{r['to_emp']}",
        "category": "Knows", "label": r["connection_type"],
        "strength": r["strength"],
    }} for r in connections]
    return {"data": rows, "elements": {"nodes": nodes, "edges": edges},
            "message": f"Mạng lưới trong bán kính {k} bước."}


def _audit_after(connection: oracledb.Connection, before_id: int,
                 action: str, record_id: str) -> dict[str, Any] | None:
    return query_one(connection, """
        SELECT log_id, table_name, action, record_id, old_value, new_value,
               changed_by, changed_at
        FROM audit_log
        WHERE log_id > :before_id AND table_name = 'KNOWS'
          AND action = :action AND record_id = :record_id
        ORDER BY log_id DESC FETCH FIRST 1 ROW ONLY
    """, {"before_id": before_id, "action": action, "record_id": record_id})


def _last_audit_id(connection: oracledb.Connection) -> int:
    return int(scalar(connection, "SELECT NVL(MAX(log_id), 0) FROM audit_log") or 0)


def _check_connection_editable(connection: oracledb.Connection, from_emp: int, to_emp: int) -> None:
    """Lock row and protect auto-generated TEAMMATE provenance.

    Manual changes to an auto edge would silently break the project membership
    invariant, so only project_members DML is allowed to remove/update such edges.
    """
    with connection.cursor() as cursor:
        cursor.execute("""SELECT connection_type, notes FROM knows
            WHERE from_emp=:a AND to_emp=:b FOR UPDATE""",
            {"a": from_emp, "b": to_emp})
        item = cursor.fetchone()
    if item is None:
        raise api_error(404, "CONNECTION_NOT_FOUND", "Quan hệ kết nối không tồn tại.")
    if item[0] == "TEAMMATE" and (item[1] or "").startswith("Auto-created from project "):
        raise api_error(409, "AUTO_TEAMMATE_PROTECTED",
                        "TEAMMATE do trigger tạo; hãy sửa/gỡ thành viên dự án để đồng bộ quan hệ.")


def _check_manual_notes(notes: str | None) -> None:
    if notes and notes.startswith("Auto-created from project "):
        raise api_error(422, "RESERVED_NOTES", "Tiền tố ghi chú này dành riêng cho trigger TEAMMATE.")


def connection_create(connection: oracledb.Connection, body: ConnectionCreate) -> dict[str, Any]:
    _check_manual_notes(body.notes)
    before = _last_audit_id(connection)
    with connection.cursor() as cursor:
        # Package must not COMMIT; db_action owns the transaction.
        cursor.callproc("pkg_social_network.create_connection", [
            body.from_emp, body.to_emp, body.connection_type, float(body.strength), body.notes
        ])
    record_id = f"{body.from_emp}->{body.to_emp}"
    audit = _audit_after(connection, before, "INSERT", record_id)
    record = query_one(connection, """
        SELECT from_emp, to_emp, connection_type, strength, since_date, notes
        FROM knows WHERE from_emp = :from_emp AND to_emp = :to_emp
    """, {"from_emp": body.from_emp, "to_emp": body.to_emp})
    message = "Tạo kết nối thành công!"
    if audit:
        message += f" Trigger trg_audit_knows đã ghi log #{audit['log_id']}"
    return {"success": True, "ok": True, "message": message, "record": record, "audit_log": audit}


def connection_update(connection: oracledb.Connection, body: ConnectionUpdate) -> dict[str, Any]:
    modified = body.model_fields_set & {"connection_type", "strength", "notes"}
    if not modified:
        raise api_error(400, "NOTHING_TO_UPDATE", "Cần cung cấp ít nhất một trường để cập nhật.")
    if ("connection_type" in modified and body.connection_type is None
            or "strength" in modified and body.strength is None):
        raise api_error(400, "INVALID_UPDATE", "Loại quan hệ và độ mạnh không được là null.")
    if "notes" in modified:
        _check_manual_notes(body.notes)
    _check_connection_editable(connection, body.from_emp, body.to_emp)
    before = _last_audit_id(connection)
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE knows SET
              connection_type = CASE WHEN :change_type = 1 THEN :connection_type ELSE connection_type END,
              strength = CASE WHEN :change_strength = 1 THEN CAST(:strength AS NUMBER(3,2)) ELSE strength END,
              notes = CASE WHEN :change_notes = 1 THEN :notes ELSE notes END
            WHERE from_emp = :from_emp AND to_emp = :to_emp
        """, {
            "change_type": int("connection_type" in modified),
            "change_strength": int("strength" in modified),
            "change_notes": int("notes" in modified),
            "connection_type": body.connection_type,
            "strength": float(body.strength) if body.strength is not None else None,
            "notes": body.notes,
            "from_emp": body.from_emp, "to_emp": body.to_emp,
        })
        if cursor.rowcount == 0:
            raise api_error(404, "CONNECTION_NOT_FOUND", "Quan hệ kết nối không tồn tại.")
    record = query_one(connection, """
        SELECT from_emp, to_emp, connection_type, strength, notes
        FROM knows WHERE from_emp = :from_emp AND to_emp = :to_emp
    """, {"from_emp": body.from_emp, "to_emp": body.to_emp})
    audit = _audit_after(connection, before, "UPDATE", f"{body.from_emp}->{body.to_emp}")
    return {"message": "Cập nhật quan hệ thành công.", "record": record, "audit_log": audit}


def connection_delete(connection: oracledb.Connection, body: ConnectionDelete) -> dict[str, Any]:
    _check_connection_editable(connection, body.from_emp, body.to_emp)
    before = _last_audit_id(connection)
    with connection.cursor() as cursor:
        cursor.execute("""
            DELETE FROM knows WHERE from_emp = :from_emp AND to_emp = :to_emp
        """, {"from_emp": body.from_emp, "to_emp": body.to_emp})
        if cursor.rowcount == 0:
            raise api_error(404, "CONNECTION_NOT_FOUND", "Quan hệ kết nối không tồn tại.")
    audit = _audit_after(connection, before, "DELETE", f"{body.from_emp}->{body.to_emp}")
    return {"message": "Đã xóa quan hệ kết nối.", "record": {
        "from_emp": body.from_emp, "to_emp": body.to_emp}, "audit_log": audit}


def add_project_member(connection: oracledb.Connection, project_id: int,
                       body: ProjectMemberCreate) -> dict[str, Any]:
    find_employee(connection, body.employee_id, active=True)
    project = query_one(connection, """
        SELECT project_id, project_name, status FROM projects
        WHERE project_id = :project_id
    """, {"project_id": project_id})
    require_found(project, "dự án")
    if project["status"] in {"COMPLETED", "CANCELLED"}:
        raise api_error(400, "PROJECT_CLOSED", "Không thể thêm thành viên vào dự án đã đóng/hủy.")
    old_count = int(scalar(connection, "SELECT COUNT(*) FROM knows"))
    previous = query_all(connection, """
        SELECT from_emp, to_emp FROM knows
        WHERE (from_emp = :emp_id OR to_emp = :emp_id)
          AND connection_type = 'TEAMMATE'
    """, {"emp_id": body.employee_id})
    old_edges = {(int(r["from_emp"]), int(r["to_emp"])) for r in previous}
    with connection.cursor() as cursor:
        cursor.execute("""
            INSERT INTO project_members (employee_id, project_id, role)
            VALUES (:employee_id, :project_id, :member_role)
        """, {"employee_id": body.employee_id, "project_id": project_id,
               "member_role": body.role})
    new_count = int(scalar(connection, "SELECT COUNT(*) FROM knows"))
    after = query_all(connection, """
        SELECT k.from_emp, k.to_emp, k.connection_type, k.strength, k.notes
        FROM knows k
        WHERE (k.from_emp = :emp_id OR k.to_emp = :emp_id)
          AND k.connection_type = 'TEAMMATE'
    """, {"emp_id": body.employee_id})
    created = [row for row in after
               if (int(row["from_emp"]), int(row["to_emp"])) not in old_edges]
    return {
        "message": "Thêm thành viên dự án thành công.",
        "project_id": project_id, "employee_id": body.employee_id,
        "role": body.role, "knows_before": old_count,
        "knows_after": new_count, "net_new_connections": new_count - old_count,
        "new_teammate_edges": created,
        "new_teammate_edge_count": len(created),
        "warning": ("Không có TEAMMATE mới do cạnh đã tồn tại hoặc dự án chưa có đồng đội."
                    if not created else None),
    }


def stats(connection: oracledb.Connection) -> dict[str, Any]:
    counts = query_one(connection, """
        SELECT (SELECT COUNT(*) FROM employees) AS employees,
               (SELECT COUNT(*) FROM departments) AS departments,
               (SELECT COUNT(*) FROM projects) AS projects,
               (SELECT COUNT(*) FROM reports_to) AS reports_to,
               (SELECT COUNT(*) FROM project_members) AS works_on,
               (SELECT COUNT(*) FROM knows) AS knows,
               (SELECT COUNT(*) FROM audit_log) AS audit_logs
        FROM dual
    """)
    vertices = {key: int(counts[key]) for key in ("employees", "departments", "projects")}
    vertices["total"] = sum(vertices.values())
    edges = {key: int(counts[key]) for key in ("reports_to", "works_on", "knows")}
    edges["total"] = sum(edges.values())
    connection_types = query_all(connection, """
        SELECT connection_type, COUNT(*) AS total FROM knows
        GROUP BY connection_type ORDER BY total DESC
    """)
    return {"vertices": vertices, "edges": edges,
            "audit_logs": int(counts["audit_logs"]),
            "connection_types": connection_types}


def audit_logs(connection: oracledb.Connection, limit: int,
               action: str | None = None) -> list[dict[str, Any]]:
    return query_all(connection, """
        SELECT log_id, table_name, action, record_id,
               old_value, new_value, changed_by, changed_at
        FROM audit_log
        WHERE (:action IS NULL OR action = :action)
        ORDER BY log_id DESC FETCH FIRST :row_limit ROWS ONLY
    """, {"action": action, "row_limit": limit})


def demo_presets() -> list[dict[str, Any]]:
    # Illustrative IDs are based on 02_sample_data.sql, not live computed paths.
    return [
        {"name": "Junior Backend → CEO", "endpoint": "/api/graph/shortest-path",
         "body": {"source_id": 20, "target_id": 1, "max_hops": 6, "include_projects": False}},
        {"name": "Developer Hà Nội → Đà Nẵng", "endpoint": "/api/graph/shortest-path",
         "body": {"source_id": 53, "target_id": 58, "max_hops": 5, "include_projects": True}},
        {"name": "Cấp dưới Giám đốc Công nghệ", "endpoint": "/api/graph/subordinates/3"},
        {"name": "Đồng đội nhân viên #9", "endpoint": "/api/graph/teammates/9"},
        {"name": "Mạng 2-hops nhân viên #8", "endpoint": "/api/graph/khops/8?k=2"},
    ]
