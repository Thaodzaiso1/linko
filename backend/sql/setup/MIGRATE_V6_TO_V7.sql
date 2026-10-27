-- Apply with SQLcl / SQL*Plus / SQL Developer F5 on the existing V6 owner schema.
-- NON-DESTRUCTIVE migration. DDL implicitly commits; BACK UP first.
WHENEVER SQLERROR EXIT SQL.SQLCODE
@@09_v7_full_audit.sql
@@06_validation.sql
PROMPT LINKO V6 -> V7 MIGRATION COMPLETE
