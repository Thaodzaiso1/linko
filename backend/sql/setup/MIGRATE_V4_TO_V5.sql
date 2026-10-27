-- NON-DESTRUCTIVE upgrade: keeps all seven tables, IDs and current data.
-- Run with SQLcl/SQL*Plus connected as the schema owner. Back up DB first.
-- DDL implicitly commits, so take a backup before applying.
WHENEVER SQLERROR EXIT SQL.SQLCODE
@@04_plsql.sql
@@07_v5_teammate_sync.sql
@@08_reconcile_teammates.sql
@@06_validation.sql
PROMPT LINKO V4 -> V5 MIGRATION COMPLETE
