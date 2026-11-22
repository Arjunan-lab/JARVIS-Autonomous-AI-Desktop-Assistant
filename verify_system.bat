@echo off
setlocal
echo ========================================================
echo   JARVIS Automated End-to-End System Quality Gate Check
echo ========================================================
echo.

set ROOT_DIR=%~dp0
set FAIL_COUNT=0

echo [1/5] Running Backend Linter (ruff)...
cd /d "%ROOT_DIR%backend"
call .venv\Scripts\ruff.exe check app tests
if errorlevel 1 (
    echo [FAIL] Backend lint check failed!
    set /a FAIL_COUNT+=1
) else (
    echo [PASS] Backend lint check clean.
)
echo.

echo [2/5] Running Backend Automated Tests (pytest)...
call .venv\Scripts\python.exe -m pytest -q
if errorlevel 1 (
    echo [FAIL] Backend pytest failed!
    set /a FAIL_COUNT+=1
) else (
    echo [PASS] Backend pytest passed.
)
echo.

echo [3/5] Running Frontend Automated Tests (vitest)...
cd /d "%ROOT_DIR%desktop"
call npm test
if errorlevel 1 (
    echo [FAIL] Frontend vitest failed!
    set /a FAIL_COUNT+=1
) else (
    echo [PASS] Frontend vitest passed.
)
echo.

echo [4/5] Running Frontend Strict Type Check (tsc)...
call npm run typecheck
if errorlevel 1 (
    echo [FAIL] Frontend typecheck failed!
    set /a FAIL_COUNT+=1
) else (
    echo [PASS] Frontend typecheck passed.
)
echo.

echo [5/5] Building Frontend Production Bundle (vite build)...
call npm run build
if errorlevel 1 (
    echo [FAIL] Frontend production build failed!
    set /a FAIL_COUNT+=1
) else (
    echo [PASS] Frontend production build succeeded.
)
echo.

cd /d "%ROOT_DIR%"
echo ========================================================
if %FAIL_COUNT% gtr 0 (
    echo [RESULT] System Verification FAILED with %FAIL_COUNT% errors.
    exit /b 1
) else (
    echo [RESULT] ALL QUALITY GATES PASSED! System is operational.
)
if "%~1"=="--no-pause" goto :done
if "%CI%"=="" pause
:done
exit /b %FAIL_COUNT%
