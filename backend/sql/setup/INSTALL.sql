-- SQLcl or SQL*Plus: connect as application schema to Oracle 23ai PDB first.
-- WARNING: This DROPS/RECREATES the seven project tables and deletes old data.
WHENEVER SQLERROR EXIT SQL.SQLCODE
@@01_schema.sql
@@02_sample_data.sql
@@03_property_graph.sql
@@04_plsql.sql
@@07_v5_teammate_sync.sql
@@08_reconcile_teammates.sql
@@09_v7_full_audit.sql
@@06_validation.sql
PROMPT LINKO INSTALL COMPLETE
