# Linko deployment

Use Render Blueprint with root render.yaml or create a Docker Web Service pointing to this repository, branch main. Frontend React and backend FastAPI share one origin.

Set LINKO_ADMIN_PASSWORD in Render Environment (never commit passwords). Default Blueprint uses USE_MOCK=true, which is DEMO DATA, NOT Oracle 23ai. To connect Oracle 23ai set USE_MOCK=false, LINKO_STRICT_ORACLE=true and ORACLE_USER, ORACLE_PASSWORD, ORACLE_CONNECT_STRING, and ensure network connectivity. Render does not create the Oracle database.

Local backend: set LINKO_ALLOW_DEMO_USERS=true and USE_MOCK=true, then run uvicorn main:app --reload from Linko_V2/linko-fastapi/linko-fastapi.
Frontend: npm ci && npm run dev from Linko_V2/linko-web.
The optional social feed uses ephemeral SQLite on free Render, which loses local data on redeploy/restart. Production requires durable storage and stronger authentication.
