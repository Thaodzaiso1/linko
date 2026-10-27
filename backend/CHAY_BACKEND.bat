@echo off
cd /d "%~dp0"
if not exist .env (
    echo Missing .env -- copy .env.example and enter Oracle connection details.
    pause
    exit /b 1
)
py -m pip install -r requirements.txt || exit /b 1
py tools\doctor.py
if errorlevel 1 (
   echo Oracle verification failed. Fix Oracle/.env, then rerun.
   pause
   exit /b 1
)
py -m uvicorn main:app --host 127.0.0.1 --port 8000
