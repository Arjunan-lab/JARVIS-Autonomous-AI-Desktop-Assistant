@echo off
setlocal
echo ========================================================
echo   JARVIS AI Assistant - Starting Desktop Frontend Shell
echo ========================================================
cd /d "%~dp0desktop"

if not exist "node_modules" (
    echo [INFO] Installing frontend npm dependencies...
    call npm install
)

echo [INFO] Launching Vite development server for JARVIS Cockpit...
echo Open your browser or Tauri webview at: http://localhost:5173
echo.
echo NOTE: If Visual Studio "Desktop development with C++" is installed,
echo you can launch the native Tauri application with: npm run tauri dev
echo.

call npm run dev

pause
