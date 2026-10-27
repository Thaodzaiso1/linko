# Changelog V5

## Backwards compatible
- V4 HTTP endpoints preserved. No changes to the seven-table schema.
- New operations: `GET /api/ready`, `/api/network/integrity`, `/api/stats/cross-department`, `/api/stats/project-collaboration`.
- `/api/graph/overview` adds `truncated_edges` and caps edges at 5000.
- `X-Request-ID` added to responses.

## Breaking operational change
- Must apply `sql/setup/MIGRATE_V4_TO_V5.sql` before enabling V5 application code.
  V5 removes package-level COMMIT and delegates it to API transaction wrapper.
- `trg_auto_teammate` now maintains automatic edges after membership DELETE/UPDATE,
  not just INSERT. It never overwrites manually entered edges.
- CORS defaults to an explicit dev-origin allowlist rather than wildcard.
- Optional API_WRITE_KEY when configured protects mutating HTTP methods.

## Validation status
- 18 automated offline tests (API contracts, transaction boundaries, key guard,
  SQL allowlist, graph normalization) PASS in the packaging environment.
- Oracle 23ai integration tests and actual DDL compilation NOT run here.
  Run `tools/doctor.py` and `tools/smoke_http.py --write` against a disposable Oracle PDB.
