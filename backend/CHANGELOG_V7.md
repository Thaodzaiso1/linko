# CHANGELOG V7

- JWT authentication: local CLI-demo HS256 / enterprise OIDC RS256 and RBAC (Employee/HR/Admin) on all real `/api/*` endpoints.
- Swagger HTTP Bearer security scheme; default deny on invalid/missing auth configuration.
- Soft delete for employee; explicit Admin-only hard delete and block manager with direct reports.
- `GRAPH_TABLE` path reconstruction filters inactive intermediate Employee; explores valid path lengths up to cap.
- `09_v7_full_audit.sql`: 6 audited business tables; propagate JWT sub into `SYS_CONTEXT(USERENV, CLIENT_IDENTIFIER)` per transaction; clear pooled identity.
- SQL migration `MIGRATE_V6_TO_V7.sql` additive, installer updated, /api/ready validates V7 triggers.
- Dockerfile, docker compose, CI test job; updated real-Oracle smoke scripts to use bearer token.
- Extra fail-closed / RBAC / graph-filter tests. Existing V6 APIs preserved except deliberate employee DELETE soft-delete behavior and JWT requirement.
- No claim that Oracle 23ai or external SSO end-to-end testing ran in this environment.
