-- ============================================================
-- 04_plsql.sql
-- Package + Triggers + Procedures/Functions + Exception Handling
-- Đáp ứng yêu cầu tối thiểu PL/SQL cho đề tài Graph
-- ============================================================

-- ============================================================
-- 1. PACKAGE SPECIFICATION
-- ============================================================
CREATE OR REPLACE PACKAGE pkg_social_network AS

  -- Tìm đường ngắn nhất giữa 2 nhân viên (trả về path length)
  FUNCTION find_shortest_path_length (
    p_from_id IN NUMBER,
    p_to_id   IN NUMBER,
    p_max_hops IN NUMBER DEFAULT 6
  ) RETURN NUMBER;

  -- Lấy danh sách đồng đội của 1 nhân viên
  PROCEDURE get_teammates (
    p_emp_id IN NUMBER,
    p_result OUT SYS_REFCURSOR
  );

  -- Tạo quan hệ Knows mới (có exception handling)
  PROCEDURE create_connection (
    p_from_id   IN NUMBER,
    p_to_id     IN NUMBER,
    p_type      IN VARCHAR2 DEFAULT 'COLLEAGUE',
    p_strength  IN NUMBER DEFAULT 1.0,
    p_notes     IN VARCHAR2 DEFAULT NULL
  );

  -- Thống kê mạng lưới của 1 nhân viên
  FUNCTION get_network_stats (
    p_emp_id IN NUMBER
  ) RETURN VARCHAR2;

  -- Exception tùy chỉnh
  e_self_connection EXCEPTION;
  PRAGMA EXCEPTION_INIT(e_self_connection, -20001);

  e_emp_not_found EXCEPTION;
  PRAGMA EXCEPTION_INIT(e_emp_not_found, -20002);

  e_connection_exists EXCEPTION;
  PRAGMA EXCEPTION_INIT(e_connection_exists, -20003);

END pkg_social_network;
/

-- ============================================================
-- 2. PACKAGE BODY
-- ============================================================
CREATE OR REPLACE PACKAGE BODY pkg_social_network AS

  -- ----------------------------------------------------------
  -- FUNCTION: find_shortest_path_length
  -- ----------------------------------------------------------
  FUNCTION find_shortest_path_length (
    p_from_id IN NUMBER,
    p_to_id   IN NUMBER,
    p_max_hops IN NUMBER DEFAULT 6
  ) RETURN NUMBER
  IS
    v_length NUMBER := NULL;
  BEGIN
    -- Kiểm tra nhân viên tồn tại
    DECLARE
      v_cnt NUMBER;
    BEGIN
      SELECT COUNT(*) INTO v_cnt FROM employees 
      WHERE employee_id IN (p_from_id, p_to_id) AND status = 'ACTIVE';
      IF v_cnt < 2 THEN
        RAISE e_emp_not_found;
      END IF;
    END;

    -- Dùng GRAPH_TABLE để tìm path ngắn nhất
    BEGIN
      SELECT MIN(path_len) INTO v_length
      FROM GRAPH_TABLE (
        enterprise_social_graph
        MATCH (
          (a IS Employee WHERE a.employee_id = p_from_id)
          -[e IS Knows|ReportsTo]-{1,6}
          (b IS Employee WHERE b.employee_id = p_to_id)
        )
        COLUMNS ( BINDING_COUNT(e) AS path_len )
      );
    EXCEPTION
      WHEN NO_DATA_FOUND THEN
        v_length := NULL; -- Không tìm thấy đường đi
    END;

    RETURN v_length;
  EXCEPTION
    WHEN e_emp_not_found THEN
      RAISE_APPLICATION_ERROR(-20002, 'Một hoặc cả hai nhân viên không tồn tại hoặc không active');
    WHEN OTHERS THEN
      RAISE_APPLICATION_ERROR(-20099, 'Lỗi khi tìm đường đi: ' || SQLERRM);
  END find_shortest_path_length;

  -- ----------------------------------------------------------
  -- PROCEDURE: get_teammates
  -- ----------------------------------------------------------
  PROCEDURE get_teammates (
    p_emp_id IN NUMBER,
    p_result OUT SYS_REFCURSOR
  )
  IS
  BEGIN
    OPEN p_result FOR
      SELECT DISTINCT 
             t.employee_id,
             t.full_name,
             t.title,
             p.project_name,
             pm.role
      FROM project_members me
      JOIN project_members pm ON me.project_id = pm.project_id
      JOIN employees t ON pm.employee_id = t.employee_id
      JOIN projects p ON me.project_id = p.project_id
      WHERE me.employee_id = p_emp_id
        AND pm.employee_id <> p_emp_id
        AND t.status = 'ACTIVE'
      ORDER BY p.project_name, t.full_name;
  EXCEPTION
    WHEN OTHERS THEN
      RAISE_APPLICATION_ERROR(-20099, 'Lỗi khi lấy danh sách đồng đội: ' || SQLERRM);
  END get_teammates;

  -- ----------------------------------------------------------
  -- PROCEDURE: create_connection
  -- ----------------------------------------------------------
  PROCEDURE create_connection (
    p_from_id   IN NUMBER,
    p_to_id     IN NUMBER,
    p_type      IN VARCHAR2 DEFAULT 'COLLEAGUE',
    p_strength  IN NUMBER DEFAULT 1.0,
    p_notes     IN VARCHAR2 DEFAULT NULL
  )
  IS
    v_cnt NUMBER;
  BEGIN
    -- Không cho kết nối với chính mình
    IF p_from_id = p_to_id THEN
      RAISE e_self_connection;
    END IF;

    -- Kiểm tra nhân viên tồn tại
    SELECT COUNT(*) INTO v_cnt 
    FROM employees 
    WHERE employee_id IN (p_from_id, p_to_id) AND status = 'ACTIVE';
    
    IF v_cnt < 2 THEN
      RAISE e_emp_not_found;
    END IF;

    -- Kiểm tra đã tồn tại chưa
    SELECT COUNT(*) INTO v_cnt 
    FROM knows 
    WHERE from_emp = p_from_id AND to_emp = p_to_id;

    IF v_cnt > 0 THEN
      RAISE e_connection_exists;
    END IF;

    -- Insert
    INSERT INTO knows (from_emp, to_emp, connection_type, strength, notes)
    VALUES (p_from_id, p_to_id, p_type, p_strength, p_notes);

    -- Transaction is committed by the API caller (never inside this package).
  EXCEPTION
    WHEN e_self_connection THEN
      RAISE_APPLICATION_ERROR(-20001, 'Không thể tạo quan hệ với chính mình');
    WHEN e_emp_not_found THEN
      RAISE_APPLICATION_ERROR(-20002, 'Nhân viên không tồn tại hoặc không active');
    WHEN e_connection_exists THEN
      RAISE_APPLICATION_ERROR(-20003, 'Quan hệ đã tồn tại giữa hai nhân viên này');
    WHEN OTHERS THEN
      -- Caller owns ROLLBACK; package must not change a broader transaction.
      RAISE_APPLICATION_ERROR(-20099, 'Lỗi khi tạo quan hệ: ' || SQLERRM);
  END create_connection;

  -- ----------------------------------------------------------
  -- FUNCTION: get_network_stats
  -- ----------------------------------------------------------
  FUNCTION get_network_stats (
    p_emp_id IN NUMBER
  ) RETURN VARCHAR2
  IS
    v_outgoing NUMBER;
    v_incoming NUMBER;
    v_projects NUMBER;
    v_result   VARCHAR2(500);
  BEGIN
    SELECT COUNT(*) INTO v_outgoing FROM knows WHERE from_emp = p_emp_id;
    SELECT COUNT(*) INTO v_incoming FROM knows WHERE to_emp = p_emp_id;
    SELECT COUNT(*) INTO v_projects FROM project_members WHERE employee_id = p_emp_id;

    v_result := 'Outgoing: ' || v_outgoing || 
                ' | Incoming: ' || v_incoming || 
                ' | Projects: ' || v_projects;
    RETURN v_result;
  EXCEPTION
    WHEN OTHERS THEN
      RETURN 'Error: ' || SQLERRM;
  END get_network_stats;

END pkg_social_network;
/

-- ============================================================
-- 3. TRIGGER 1: Tự động tạo quan hệ TEAMMATE khi thêm vào dự án
-- ============================================================
CREATE OR REPLACE TRIGGER trg_auto_teammate
AFTER INSERT ON project_members
FOR EACH ROW
DECLARE
  CURSOR c_members IS
    SELECT employee_id 
    FROM project_members 
    WHERE project_id = :NEW.project_id 
      AND employee_id <> :NEW.employee_id;
BEGIN
  FOR r IN c_members LOOP
    -- Tạo quan hệ 2 chiều (nếu chưa có)
    BEGIN
      INSERT INTO knows (from_emp, to_emp, connection_type, strength, notes)
      VALUES (:NEW.employee_id, r.employee_id, 'TEAMMATE', 2.0, 
              'Auto-created from project ' || :NEW.project_id);
    EXCEPTION
      WHEN DUP_VAL_ON_INDEX THEN NULL; -- Đã tồn tại thì bỏ qua
    END;

    BEGIN
      INSERT INTO knows (from_emp, to_emp, connection_type, strength, notes)
      VALUES (r.employee_id, :NEW.employee_id, 'TEAMMATE', 2.0, 
              'Auto-created from project ' || :NEW.project_id);
    EXCEPTION
      WHEN DUP_VAL_ON_INDEX THEN NULL;
    END;
  END LOOP;
END;
/

-- ============================================================
-- 4. TRIGGER 2: Audit log mọi thay đổi trên bảng KNOWS
-- ============================================================
CREATE OR REPLACE TRIGGER trg_audit_knows
AFTER INSERT OR UPDATE OR DELETE ON knows
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
  v_old    VARCHAR2(4000);
  v_new    VARCHAR2(4000);
  v_id     VARCHAR2(100);
BEGIN
  IF INSERTING THEN
    v_action := 'INSERT';
    v_id := :NEW.from_emp || '->' || :NEW.to_emp;
    v_new := 'type=' || :NEW.connection_type || ', strength=' || :NEW.strength;
    v_old := NULL;
  ELSIF UPDATING THEN
    v_action := 'UPDATE';
    v_id := :NEW.from_emp || '->' || :NEW.to_emp;
    v_old := 'type=' || :OLD.connection_type || ', strength=' || :OLD.strength;
    v_new := 'type=' || :NEW.connection_type || ', strength=' || :NEW.strength;
  ELSIF DELETING THEN
    v_action := 'DELETE';
    v_id := :OLD.from_emp || '->' || :OLD.to_emp;
    v_old := 'type=' || :OLD.connection_type || ', strength=' || :OLD.strength;
    v_new := NULL;
  END IF;

  INSERT INTO audit_log (table_name, action, record_id, old_value, new_value)
  VALUES ('KNOWS', v_action, v_id, v_old, v_new);
END;
/

-- ============================================================
-- 5. Một số Procedure/Function độc lập bổ sung (đủ ≥ 3)
-- ============================================================

-- Function kiểm tra 2 người có cùng dự án không
CREATE OR REPLACE FUNCTION fn_is_teammate (
  p_emp1 IN NUMBER,
  p_emp2 IN NUMBER
) RETURN VARCHAR2
IS
  v_cnt NUMBER;
BEGIN
  SELECT COUNT(*) INTO v_cnt
  FROM project_members a
  JOIN project_members b ON a.project_id = b.project_id
  WHERE a.employee_id = p_emp1 AND b.employee_id = p_emp2;

  IF v_cnt > 0 THEN
    RETURN 'YES';
  ELSE
    RETURN 'NO';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RETURN 'ERROR';
END;
/

-- Procedure lấy cây tổ chức từ 1 manager
CREATE OR REPLACE PROCEDURE sp_get_org_tree (
  p_manager_id IN NUMBER,
  p_result OUT SYS_REFCURSOR
)
IS
BEGIN
  OPEN p_result FOR
    SELECT e.employee_id, e.full_name, e.title, LEVEL AS org_level
    FROM employees e
    JOIN reports_to r ON e.employee_id = r.employee_id
    START WITH r.manager_id = p_manager_id
    CONNECT BY PRIOR r.employee_id = r.manager_id
    ORDER SIBLINGS BY e.full_name;
EXCEPTION
  WHEN OTHERS THEN
    RAISE_APPLICATION_ERROR(-20099, 'Lỗi lấy org tree: ' || SQLERRM);
END;
/

PROMPT ===== PACKAGE + TRIGGERS + PROCEDURES CREATED SUCCESSFULLY =====

-- Test nhanh

-- Run 06_validation.sql after installing 05_fix_auto_teammate_trigger.sql.
