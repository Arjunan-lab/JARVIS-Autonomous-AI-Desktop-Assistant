@echo off
setlocal
echo ========================================================
echo   JARVIS AI Assistant - Starting System
echo ========================================================
echo Launching Backend server in a new window...
start "JARVIS Backend (Port 8000)" cmd /k "%~dp0start_backend.bat"

echo Waiting 2 seconds for backend to initialize...
timeout /t 2 /nobreak >nul

echo Launching Desktop Cockpit in a new window...
start "JARVIS Desktop Shell" cmd /k "%~dp0start_desktop.bat"

echo.
echo Both components launched!
echo - Backend API:  http://127.0.0.1:8000/api/health
echo - API Docs:     http://127.0.0.1:8000/docs
echo - Desktop App:  http://localhost:5173
echo.
echo Opening JARVIS Cockpit dashboard in your browser...
timeout /t 3 /nobreak >nul
start http://localhost:5173
echo ========================================================
