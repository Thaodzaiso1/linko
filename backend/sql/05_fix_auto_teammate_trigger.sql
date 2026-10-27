-- OPTIONAL, RECOMMENDED BEFORE TESTING POST /api/projects/{id}/members.
-- Replace the original AFTER INSERT FOR EACH ROW trigger from 04_plsql.sql,
-- which queries project_members while it is mutating (ORA-04091).
-- This preserves both-way TEAMMATE edges and the original trigger name.
-- Run while connected to the application schema, after 04_plsql.sql.

CREATE OR REPLACE TRIGGER trg_auto_teammate
FOR INSERT ON project_members
COMPOUND TRIGGER
    TYPE t_new_member IS RECORD (
        employee_id project_members.employee_id%TYPE,
        project_id project_members.project_id%TYPE
    );
    TYPE t_new_member_list IS TABLE OF t_new_member INDEX BY PLS_INTEGER;
    g_new_members t_new_member_list;
    g_member_count PLS_INTEGER := 0;

    AFTER EACH ROW IS
    BEGIN
        g_member_count := g_member_count + 1;
        g_new_members(g_member_count).employee_id := :NEW.employee_id;
        g_new_members(g_member_count).project_id := :NEW.project_id;
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        v_employee_id project_members.employee_id%TYPE;
        v_project_id  project_members.project_id%TYPE;
    BEGIN
        FOR i IN 1 .. g_member_count LOOP
            v_employee_id := g_new_members(i).employee_id;
            v_project_id := g_new_members(i).project_id;
            FOR existing_member IN (
                SELECT employee_id
                FROM project_members
                WHERE project_id = v_project_id
                  AND employee_id <> v_employee_id
            ) LOOP
                BEGIN
                    INSERT INTO knows (from_emp, to_emp, connection_type, strength, notes)
                    VALUES (
                        v_employee_id, existing_member.employee_id,
                        'TEAMMATE', 2.0,
                        'Auto-created from project ' || v_project_id
                    );
                EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL;
                END;
                BEGIN
                    INSERT INTO knows (from_emp, to_emp, connection_type, strength, notes)
                    VALUES (
                        existing_member.employee_id, v_employee_id,
                        'TEAMMATE', 2.0,
                        'Auto-created from project ' || v_project_id
                    );
                EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL;
                END;
            END LOOP;
        END LOOP;
    END AFTER STATEMENT;
END trg_auto_teammate;
/

SHOW ERRORS TRIGGER trg_auto_teammate;
