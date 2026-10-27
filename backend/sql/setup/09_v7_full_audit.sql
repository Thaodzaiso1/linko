-- LINKO V7: NON-DESTRUCTIVE audit upgrade; preserves existing seven tables.
-- Run only on the owner schema in Oracle 23ai PDB. Backup first.
-- One audited transaction = business change + audit rows; no autonomous transaction.
-- Identity comes from FastAPI python-oracledb connection.client_identifier.
-- All triggers omit email/phone to reduce sensitive-data retention.
WHENEVER SQLERROR EXIT SQL.SQLCODE

CREATE OR REPLACE TRIGGER trg_audit_employees
AFTER INSERT OR UPDATE OR DELETE ON employees
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
BEGIN
  IF INSERTING THEN v_action := 'INSERT';
  ELSIF UPDATING THEN v_action := 'UPDATE';
  ELSE v_action := 'DELETE'; END IF;
  INSERT INTO audit_log(table_name,action,record_id,old_value,new_value,changed_by)
  VALUES ('EMPLOYEES',v_action,TO_CHAR(COALESCE(:NEW.employee_id,:OLD.employee_id)),
      CASE WHEN INSERTING THEN NULL ELSE 'status='||:OLD.status||',dept='||:OLD.department_id||',title='||:OLD.title END,
      CASE WHEN DELETING THEN NULL ELSE 'status='||:NEW.status||',dept='||:NEW.department_id||',title='||:NEW.title END,
      SUBSTR(COALESCE(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'),USER),1,100));
END;
/
SHOW ERRORS TRIGGER trg_audit_employees

CREATE OR REPLACE TRIGGER trg_audit_departments
AFTER INSERT OR UPDATE OR DELETE ON departments
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
BEGIN
  IF INSERTING THEN v_action := 'INSERT';
  ELSIF UPDATING THEN v_action := 'UPDATE';
  ELSE v_action := 'DELETE'; END IF;
  INSERT INTO audit_log(table_name,action,record_id,old_value,new_value,changed_by)
  VALUES ('DEPARTMENTS',v_action,TO_CHAR(COALESCE(:NEW.department_id,:OLD.department_id)),
      CASE WHEN INSERTING THEN NULL ELSE 'name='||:OLD.department_name||',location='||:OLD.location END,
      CASE WHEN DELETING THEN NULL ELSE 'name='||:NEW.department_name||',location='||:NEW.location END,
      SUBSTR(COALESCE(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'),USER),1,100));
END;
/
SHOW ERRORS TRIGGER trg_audit_departments

CREATE OR REPLACE TRIGGER trg_audit_projects
AFTER INSERT OR UPDATE OR DELETE ON projects
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
BEGIN
  IF INSERTING THEN v_action := 'INSERT';
  ELSIF UPDATING THEN v_action := 'UPDATE';
  ELSE v_action := 'DELETE'; END IF;
  INSERT INTO audit_log(table_name,action,record_id,old_value,new_value,changed_by)
  VALUES ('PROJECTS',v_action,TO_CHAR(COALESCE(:NEW.project_id,:OLD.project_id)),
      CASE WHEN INSERTING THEN NULL ELSE 'name='||:OLD.project_name||',status='||:OLD.status||',dept='||:OLD.department_id END,
      CASE WHEN DELETING THEN NULL ELSE 'name='||:NEW.project_name||',status='||:NEW.status||',dept='||:NEW.department_id END,
      SUBSTR(COALESCE(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'),USER),1,100));
END;
/
SHOW ERRORS TRIGGER trg_audit_projects

CREATE OR REPLACE TRIGGER trg_audit_project_members
AFTER INSERT OR UPDATE OR DELETE ON project_members
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
BEGIN
  IF INSERTING THEN v_action := 'INSERT';
  ELSIF UPDATING THEN v_action := 'UPDATE';
  ELSE v_action := 'DELETE'; END IF;
  INSERT INTO audit_log(table_name,action,record_id,old_value,new_value,changed_by)
  VALUES ('PROJECT_MEMBERS',v_action,
      TO_CHAR(COALESCE(:NEW.employee_id,:OLD.employee_id))||':'||TO_CHAR(COALESCE(:NEW.project_id,:OLD.project_id)),
      CASE WHEN INSERTING THEN NULL ELSE 'role='||:OLD.role END,
      CASE WHEN DELETING THEN NULL ELSE 'role='||:NEW.role END,
      SUBSTR(COALESCE(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'),USER),1,100));
END;
/
SHOW ERRORS TRIGGER trg_audit_project_members

CREATE OR REPLACE TRIGGER trg_audit_reports_to
AFTER INSERT OR UPDATE OR DELETE ON reports_to
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
BEGIN
  IF INSERTING THEN v_action := 'INSERT';
  ELSIF UPDATING THEN v_action := 'UPDATE';
  ELSE v_action := 'DELETE'; END IF;
  INSERT INTO audit_log(table_name,action,record_id,old_value,new_value,changed_by)
  VALUES ('REPORTS_TO',v_action,TO_CHAR(COALESCE(:NEW.employee_id,:OLD.employee_id)),
      CASE WHEN INSERTING THEN NULL ELSE 'manager='||:OLD.manager_id END,
      CASE WHEN DELETING THEN NULL ELSE 'manager='||:NEW.manager_id END,
      SUBSTR(COALESCE(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'),USER),1,100));
END;
/
SHOW ERRORS TRIGGER trg_audit_reports_to

-- Replace legacy audit trigger to record the authenticated actor as well.
CREATE OR REPLACE TRIGGER trg_audit_knows
AFTER INSERT OR UPDATE OR DELETE ON knows
FOR EACH ROW
DECLARE
  v_action VARCHAR2(20);
BEGIN
  IF INSERTING THEN v_action := 'INSERT';
  ELSIF UPDATING THEN v_action := 'UPDATE';
  ELSE v_action := 'DELETE'; END IF;
  INSERT INTO audit_log(table_name,action,record_id,old_value,new_value,changed_by)
  VALUES ('KNOWS',v_action,
      TO_CHAR(COALESCE(:NEW.from_emp,:OLD.from_emp))||'->'||TO_CHAR(COALESCE(:NEW.to_emp,:OLD.to_emp)),
      CASE WHEN INSERTING THEN NULL ELSE 'type='||:OLD.connection_type||',strength='||:OLD.strength END,
      CASE WHEN DELETING THEN NULL ELSE 'type='||:NEW.connection_type||',strength='||:NEW.strength END,
      SUBSTR(COALESCE(SYS_CONTEXT('USERENV','CLIENT_IDENTIFIER'),USER),1,100));
END;
/
SHOW ERRORS TRIGGER trg_audit_knows

PROMPT LINKO V7 AUDIT TRIGGERS CREATED
