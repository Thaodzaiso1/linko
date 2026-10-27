-- ============================================================
-- 03_property_graph.sql
-- Tạo SQL Property Graph + các truy vấn Graph chính
-- Oracle Database 23ai - SQL/PGQ
-- ============================================================

-- Xóa graph cũ nếu có
BEGIN
  EXECUTE IMMEDIATE 'DROP PROPERTY GRAPH enterprise_social_graph';
EXCEPTION WHEN OTHERS THEN NULL;
END;
/

-- ============================================================
-- CREATE PROPERTY GRAPH
-- ============================================================
CREATE PROPERTY GRAPH enterprise_social_graph
  VERTEX TABLES (
    employees
      KEY (employee_id)
      LABEL Employee
      PROPERTIES (employee_id, full_name, title, email, department_id, hire_date, status),
    departments
      KEY (department_id)
      LABEL Department
      PROPERTIES (department_id, department_name, location),
    projects
      KEY (project_id)
      LABEL Project
      PROPERTIES (project_id, project_name, status, start_date, department_id)
  )
  EDGE TABLES (
    -- Quan hệ quản lý (ReportsTo)
    reports_to
      KEY (employee_id)
      SOURCE KEY (employee_id) REFERENCES employees (employee_id)
      DESTINATION KEY (manager_id) REFERENCES employees (employee_id)
      LABEL ReportsTo
      PROPERTIES (since_date),

    -- Nhân viên tham gia dự án (WorksOn)
    project_members
      KEY (employee_id, project_id)
      SOURCE KEY (employee_id) REFERENCES employees (employee_id)
      DESTINATION KEY (project_id) REFERENCES projects (project_id)
      LABEL WorksOn
      PROPERTIES (role, join_date),

    -- Quan hệ mạng xã hội (Knows)
    knows
      KEY (from_emp, to_emp)
      SOURCE KEY (from_emp) REFERENCES employees (employee_id)
      DESTINATION KEY (to_emp) REFERENCES employees (employee_id)
      LABEL Knows
      PROPERTIES (connection_type, strength, since_date)
  );

PROMPT ===== PROPERTY GRAPH CREATED SUCCESSFULLY =====
