-- Demonstration queries; optional. Requires Oracle 23ai GRAPH_TABLE.
PROMPT ===== PROPERTY GRAPH CREATED SUCCESSFULLY =====

-- ============================================================
-- CÁC TRUY VẤN GRAPH CHÍNH
-- ============================================================

-- ----------------------------------------------------------
-- Q1. Tìm đường kết nối ngắn nhất giữa 2 nhân viên (CỐT LÕI)
-- Ví dụ: tìm path từ employee_id = 20 (Junior Backend) đến employee_id = 1 (CEO)
-- ----------------------------------------------------------
PROMPT ===== Q1: Shortest Path giữa 2 nhân viên =====

SELECT *
FROM GRAPH_TABLE (
  enterprise_social_graph
  MATCH (
    (a IS Employee WHERE a.employee_id = 20)
    -[e IS Knows|ReportsTo]-{1,6}
    (b IS Employee WHERE b.employee_id = 1)
  )
  COLUMNS (
    a.full_name AS from_employee,
    b.full_name AS to_employee,
    BINDING_COUNT(e) AS path_length
  )
);

-- Phiên bản dùng ONE ROW PER STEP để lấy chi tiết từng bước
PROMPT ===== Q1b: Chi tiết từng bước trên đường đi =====

SELECT *
FROM GRAPH_TABLE (
  enterprise_social_graph
  MATCH (
    (src IS Employee WHERE src.employee_id = 20)
    -[e IS Knows|ReportsTo]-{1,5}
    (dst IS Employee WHERE dst.employee_id = 3)
  )
  ONE ROW PER STEP (v1, e, v2)
  COLUMNS (
    vertex_id(v1) AS step_from_id,
    v1.full_name AS step_from_name,
    edge_id(e) AS edge_id,
    vertex_id(v2) AS step_to_id,
    v2.full_name AS step_to_name
  )
);

-- ----------------------------------------------------------
-- Q2. Tìm tất cả cấp dưới (direct + indirect) của 1 manager
-- ----------------------------------------------------------
PROMPT ===== Q2: Tất cả cấp dưới của Giám đốc Công nghệ (id=3) =====

SELECT DISTINCT emp_name, level_num
FROM GRAPH_TABLE (
  enterprise_social_graph
  MATCH (
    (m IS Employee WHERE m.employee_id = 3)
    <-[r IS ReportsTo]-{1,5}
    (e IS Employee)
  )
  COLUMNS (
    e.full_name AS emp_name,
    BINDING_COUNT(r) AS level_num
  )
)
ORDER BY level_num, emp_name;

-- ----------------------------------------------------------
-- Q3. Tìm đồng đội cùng dự án (thông qua WorksOn)
-- ----------------------------------------------------------
PROMPT ===== Q3: Đồng đội của nhân viên id=9 =====

SELECT DISTINCT teammate_name, project_name, role_in_project
FROM GRAPH_TABLE (
  enterprise_social_graph
  MATCH (
    (me IS Employee WHERE me.employee_id = 9)
    -[w1 IS WorksOn]-> (p IS Project)
    <-[w2 IS WorksOn]- (teammate IS Employee)
  )
  WHERE teammate.employee_id <> 9
  COLUMNS (
    teammate.full_name AS teammate_name,
    p.project_name AS project_name,
    w2.role AS role_in_project
  )
)
ORDER BY project_name, teammate_name;

-- ----------------------------------------------------------
-- Q4. Tìm người có thể kết nối trong 2 hops (Knows)
-- ----------------------------------------------------------
PROMPT ===== Q4: Người trong bán kính 2 hops từ id=8 =====

SELECT DISTINCT reached_name, hops
FROM GRAPH_TABLE (
  enterprise_social_graph
  MATCH (
    (start IS Employee WHERE start.employee_id = 8)
    -[k IS Knows]-{1,2}
    (reached IS Employee)
  )
  WHERE reached.employee_id <> 8
  COLUMNS (
    reached.full_name AS reached_name,
    BINDING_COUNT(k) AS hops
  )
)
ORDER BY hops, reached_name;

-- ----------------------------------------------------------
-- Q5. Tìm đường đi kết hợp nhiều loại quan hệ
-- (ReportsTo + Knows + WorksOn) giữa 2 người ở 2 chi nhánh
-- ----------------------------------------------------------
PROMPT ===== Q5: Đường kết nối đa loại quan hệ =====

SELECT *
FROM GRAPH_TABLE (
  enterprise_social_graph
  MATCH (
    (a IS Employee WHERE a.employee_id = 53)   -- Developer HN
    -[e IS Knows|ReportsTo|WorksOn]-{1,5}
    (b IS Employee WHERE b.employee_id = 58)   -- Developer DN
  )
  COLUMNS (
    a.full_name AS from_emp,
    b.full_name AS to_emp,
    BINDING_COUNT(e) AS path_length
  )
);

-- ----------------------------------------------------------
-- Q6. Thống kê số lượng kết nối theo loại
-- ----------------------------------------------------------
PROMPT ===== Q6: Thống kê quan hệ Knows =====

SELECT connection_type, COUNT(*) AS total
FROM knows
GROUP BY connection_type
ORDER BY total DESC;

PROMPT ===== ALL GRAPH QUERIES COMPLETED =====
