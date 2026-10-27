-- V5 - replace V4 insert-only trigger. Safe on existing data (no DROP TABLE).
-- Keeps the original trigger name. Single project_members statement is processed
-- after the statement, avoiding ORA-04091 (mutating table).
-- Existing manually maintained Knows edges are NEVER overwritten/deleted.
-- Automatic ownership is recognized by connection_type=TEAMMATE AND notes prefix.
CREATE OR REPLACE TRIGGER trg_auto_teammate
FOR INSERT OR UPDATE OR DELETE ON project_members
COMPOUND TRIGGER
    TYPE t_employee_ids IS TABLE OF project_members.employee_id%TYPE INDEX BY PLS_INTEGER;
    g_ids t_employee_ids;
    g_count PLS_INTEGER := 0;

    AFTER EACH ROW IS
    BEGIN
        IF INSERTING OR UPDATING THEN
            g_count := g_count + 1;
            g_ids(g_count) := :NEW.employee_id;
        END IF;
        IF DELETING OR UPDATING THEN
            g_count := g_count + 1;
            g_ids(g_count) := :OLD.employee_id;
        END IF;
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        v_shared_project NUMBER;
    BEGIN
        FOR i IN 1 .. g_count LOOP
            -- Recreate auto relations for current shared-project pairs.
            FOR peer IN (
                SELECT pm2.employee_id AS peer_id, MIN(pm1.project_id) AS shared_project
                FROM project_members pm1
                JOIN project_members pm2 ON pm2.project_id = pm1.project_id
                WHERE pm1.employee_id = g_ids(i)
                  AND pm2.employee_id <> g_ids(i)
                GROUP BY pm2.employee_id
            ) LOOP
                BEGIN
                    INSERT INTO knows(from_emp,to_emp,connection_type,strength,notes)
                    VALUES(g_ids(i),peer.peer_id,'TEAMMATE',2,
                           'Auto-created from project '||peer.shared_project);
                EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL;
                END;
                BEGIN
                    INSERT INTO knows(from_emp,to_emp,connection_type,strength,notes)
                    VALUES(peer.peer_id,g_ids(i),'TEAMMATE',2,
                           'Auto-created from project '||peer.shared_project);
                EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL;
                END;
            END LOOP;

            -- Remove only AUTO-owned TEAMMATE edges if no shared project remains.
            -- Re-point provenance when the old project was removed but another
            -- shared project still exists. Audit is handled by trg_audit_knows.
            FOR old_edge IN (
                SELECT k.from_emp, k.to_emp, k.notes
                FROM knows k
                WHERE k.connection_type = 'TEAMMATE'
                  AND k.notes LIKE 'Auto-created from project %'
                  AND (k.from_emp = g_ids(i) OR k.to_emp = g_ids(i))
            ) LOOP
                SELECT MIN(a.project_id) INTO v_shared_project
                FROM project_members a
                JOIN project_members b ON a.project_id = b.project_id
                WHERE a.employee_id = old_edge.from_emp
                  AND b.employee_id = old_edge.to_emp;

                IF v_shared_project IS NULL THEN
                    DELETE FROM knows
                    WHERE from_emp = old_edge.from_emp AND to_emp = old_edge.to_emp
                      AND connection_type = 'TEAMMATE'
                      AND notes LIKE 'Auto-created from project %';
                ELSIF old_edge.notes <> 'Auto-created from project ' || v_shared_project THEN
                    UPDATE knows SET notes = 'Auto-created from project '||v_shared_project
                    WHERE from_emp = old_edge.from_emp AND to_emp = old_edge.to_emp
                      AND connection_type = 'TEAMMATE'
                      AND notes LIKE 'Auto-created from project %';
                END IF;
            END LOOP;
        END LOOP;
    END AFTER STATEMENT;
END trg_auto_teammate;
/
SHOW ERRORS TRIGGER trg_auto_teammate;
