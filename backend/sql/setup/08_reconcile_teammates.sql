-- One-time non-destructive repair. IMPORTANT: backs up data before migration.
-- This backfills missing automatic TEAMMATE edges after sample data import,
-- removes *stale managed* edges, and preserves any manually created knows edges.
DECLARE
    v_project_id NUMBER;
BEGIN
    FOR team IN (
        SELECT pm1.employee_id AS from_emp, pm2.employee_id AS to_emp,
               MIN(pm1.project_id) AS shared_project
        FROM project_members pm1
        JOIN project_members pm2 ON pm2.project_id = pm1.project_id
        WHERE pm1.employee_id <> pm2.employee_id
        GROUP BY pm1.employee_id, pm2.employee_id
    ) LOOP
        BEGIN
            INSERT INTO knows(from_emp,to_emp,connection_type,strength,notes)
            VALUES(team.from_emp,team.to_emp,'TEAMMATE',2,
                   'Auto-created from project '||team.shared_project);
        EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL;
        END;
    END LOOP;
    FOR old_edge IN (
        SELECT from_emp,to_emp,notes FROM knows
        WHERE connection_type='TEAMMATE' AND notes LIKE 'Auto-created from project %'
    ) LOOP
        SELECT MIN(a.project_id) INTO v_project_id
        FROM project_members a JOIN project_members b ON a.project_id=b.project_id
        WHERE a.employee_id=old_edge.from_emp AND b.employee_id=old_edge.to_emp;
        IF v_project_id IS NULL THEN
            DELETE FROM knows WHERE from_emp=old_edge.from_emp AND to_emp=old_edge.to_emp
              AND connection_type='TEAMMATE' AND notes LIKE 'Auto-created from project %';
        ELSIF old_edge.notes <> 'Auto-created from project ' || v_project_id THEN
            UPDATE knows SET notes='Auto-created from project '||v_project_id
            WHERE from_emp=old_edge.from_emp AND to_emp=old_edge.to_emp
              AND connection_type='TEAMMATE' AND notes LIKE 'Auto-created from project %';
        END IF;
    END LOOP;
END;
/
COMMIT;
PROMPT V5 TEAMMATE RECONCILIATION COMPLETE
