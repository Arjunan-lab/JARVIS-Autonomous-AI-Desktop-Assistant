# JARVIS — DevOps, Deployment & Operations Runbook

**Document Version:** 1.0.0  
**Status:** Approved / Base-Lined  
**Classification:** DevOps & Systems Engineering  

---

## 1. System Prerequisites & Environment Setup

JARVIS is built to operate reliably on Windows 11 workstations with minimal external dependencies.

### 1.1 Workstation Requirements
- **Operating System:** Windows 11 64-bit (Build 22000 or higher).
- **Python Runtime:** Python 3.12 (standard 64-bit installer with `Add python.exe to PATH` enabled).
- **Node.js Runtime:** Node.js v20.x or v22.x LTS with `npm` package manager.
- **Web Browser / Webview:** Modern Chromium-based browser (Google Chrome or Microsoft Edge) with WebRTC and microphone permissions enabled.
- **Hardware:** Dual-core x64 CPU minimum, 4 GB RAM minimum, microphone input device, audio output device.

---

## 2. Configuration Reference (`backend/.env`)

All configurable operational parameters are controlled via `backend/.env`.

```ini
# Application Metadata
APP_NAME=JARVIS
APP_ENV=development
HOST=127.0.0.1
PORT=8000

# AI Provider: "gemini" (free tier Google AI Studio) or "openai"
AI_PROVIDER=gemini

# Google Gemini Configuration (https://aistudio.google.com/)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
GEMINI_VOICE=Puck

# OpenAI Realtime Configuration (https://platform.openai.com/)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_REALTIME_MODEL=gpt-realtime-mini
OPENAI_REALTIME_VOICE=marin

# Persistence & Storage
DATABASE_URL=sqlite:///./jarvis.db
JARVIS_DATA_DIR=
JARVIS_ALLOWED_DIRS=

# Budget Safeguards
JARVIS_MAX_DAILY_API_BUDGET_USD=1.00

# Networking & Logging
FRONTEND_ORIGIN=http://localhost:5173
LOG_LEVEL=INFO
```

---

## 3. Turnkey Launch Automation Scripts

Four purpose-built Windows batch scripts automate routine developer and user operations:

### 3.1 Master Launcher (`start_jarvis.bat`)
Launches both the FastAPI backend server and the desktop Vite interface in separate, color-coded Command Prompt windows with clean dependency detection.
```cmd
.\start_jarvis.bat
```

### 3.2 Backend Launcher (`start_backend.bat`)
Automates virtual environment creation (`.venv`), pip package installation, database migration checks, and starts Uvicorn with auto-reload:
```cmd
.\start_backend.bat
```

### 3.3 Desktop Launcher (`start_desktop.bat`)
Verifies Node.js dependencies (`npm install` if `node_modules` missing) and starts the Vite development server on port 5173:
```cmd
.\start_desktop.bat
```

### 3.4 System Verification Suite (`verify_system.bat`)
Runs the complete automated quality suite (46 Pytest backend tests, TypeScript validation, 44 Vitest frontend tests) before deployment:
```cmd
.\verify_system.bat
```

---

## 4. Operational Troubleshooting & Runbook

### Issue 1: "Maximum concurrent voice sessions limit (2) reached"
- **Symptom:** UI displays red alert banner upon clicking "Start Voice".
- **Root Cause:** A previous session terminated abruptly (e.g. browser tab was closed or reloaded), leaving `budget_active_sessions` incremented in `user_settings`.
- **Resolution:**
  1. Restart the backend: Lifespan hooks automatically reset active sessions to zero on startup.
  2. Or run this one-line database reset command:
     ```powershell
     cd backend
     .venv\Scripts\python.exe -c "from app.db.session import SessionLocal; from app.db.models import UserSetting; db = SessionLocal(); s = db.query(UserSetting).filter(UserSetting.key == 'budget_active_sessions').first(); s.value = '0'; db.commit(); db.close()"
     ```

### Issue 2: Port 8000 or 5173 Conflict / Already Bound
- **Symptom:** Backend fails with `[Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`.
- **Resolution:** Identify and terminate the orphaned process:
  ```powershell
  # Find process occupying port 8000
  Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
  # Terminate process (replace <PID> with process ID)
  Stop-Process -Id <PID> -Force
  ```

### Issue 3: SQLite Database Locked (`OperationalError`)
- **Symptom:** Database write queries hang or throw `database is locked`.
- **Resolution:** Verify WAL (Write-Ahead Logging) mode is enabled:
  ```powershell
  cd backend
  .venv\Scripts\python.exe -c "import sqlite3; con = sqlite3.connect('jarvis.db'); print(con.execute('PRAGMA journal_mode;').fetchall()); con.execute('PRAGMA journal_mode=WAL;'); con.commit(); con.close()"
  ```

### Issue 4: Missing or Invalid API Key
- **Symptom:** Session creation fails with HTTP 500: `Google Gemini API key is missing or not configured`.
- **Resolution:**
  1. Open `backend/.env`.
  2. Verify that `GEMINI_API_KEY` contains a valid key from [Google AI Studio](https://aistudio.google.com/).
  3. Verify `AI_PROVIDER=gemini` is selected.
  4. Save the file; Uvicorn will automatically reload.

### Issue 5: Microphone Permission Blocked in Browser
- **Symptom:** Clicking "Start Voice" produces `NotAllowedError: Permission denied`.
- **Resolution:**
  1. In Chrome / Edge, click the lock/settings icon in the URL address bar next to `http://localhost:5173/`.
  2. Under **Permissions**, toggle **Microphone** to **Allow**.
  3. Reload the browser page (`F5`).
