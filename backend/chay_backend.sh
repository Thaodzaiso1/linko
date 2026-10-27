#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo 'Missing .env: cp .env.example .env and edit connection details.'; exit 1; }
python -m pip install -r requirements.txt
python tools/doctor.py
exec python -m uvicorn main:app --host 127.0.0.1 --port 8000
