@echo off
setlocal
echo ========================================================
echo   JARVIS AI Assistant - Starting FastAPI Backend
echo ========================================================
cd /d "%~dp0backend"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in backend\.venv
    echo Please create it with:
    echo   cd backend
    echo   py -3.12 -m venv .venv
    echo   .venv\Scripts\pip install -e .[dev]
    pause
    exit /b 1
)

if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating backend\.env from .env.example
        copy .env.example .env
    )
)

echo [INFO] Running database migrations...
call .venv\Scripts\alembic.exe upgrade head
if errorlevel 1 (
    echo [WARNING] Alembic migrations encountered an issue, proceeding...
)

echo [INFO] Launching Uvicorn ASGI server on http://127.0.0.1:8000 ...
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

pause
