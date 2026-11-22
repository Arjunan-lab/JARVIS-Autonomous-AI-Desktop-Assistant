# JARVIS — Personal AI Desktop Assistant

JARVIS is a locally installed, enterprise-grade personal AI desktop assistant engineered for Windows 11. It pairs hybrid cloud reasoning via OpenAI Realtime with local SQLite persistence, strict approval-first computer automation, sandboxed filesystem access, and API budget safeguards.

---

## 📚 Software Engineering Process (SEP) Documentation

Comprehensive enterprise-grade engineering specifications for each phase of the project lifecycle are available in the [`docs/`](docs/) directory:

- 📋 [**01. Software Requirements Specification (SRS)**](docs/01_SOFTWARE_REQUIREMENTS_SPECIFICATION.md) — Functional/Non-Functional requirements, personas, traceability matrix.
- 🏛️ [**02. High-Level Design & System Architecture (HLD)**](docs/02_HIGH_LEVEL_DESIGN_ARCHITECTURE.md) — Topology, dual-provider engine, audio DSP pipeline, sequence diagrams.
- ⚙️ [**03. Low-Level Design & Data Models (LLD)**](docs/03_LOW_LEVEL_DESIGN_AND_DATA_MODELS.md) — Database schema, REST/WebSocket contracts, ToolRegistry signatures, budget algorithms.
- 🛡️ [**04. Security, Governance & Threat Model (SEC)**](docs/04_SECURITY_AND_GOVERNANCE_SPECIFICATION.md) — STRIDE threat matrix, HITL approval state machine, sandboxing, secret safety.
- 🧪 [**05. Test Plan & Quality Assurance (QA)**](docs/05_TEST_PLAN_AND_QUALITY_ASSURANCE.md) — 4 Quality gates, 46 backend tests, 44 frontend tests, mocking architecture.
- 🚀 [**06. DevOps, Deployment & Operations Runbook (OPS)**](docs/06_DEVOPS_DEPLOYMENT_AND_RUNBOOK.md) — Environment reference, Windows batch automation, troubleshooting guide.
- 📖 [**07. User Manual & Operational Guide (USER)**](docs/07_USER_MANUAL_AND_OPERATIONAL_GUIDE.md) — Voice cockpit guide, orb visual states, command catalog, approval review.
- 📑 [**Master Documentation Index & Dossier**](docs/INDEX.md) — System certification report and engineering milestone summary.

---

## 1. Architecture Overview

```text
User: Voice (WebRTC) / Push-to-Talk / Typed Input
                  │
                  ▼
       Tauri 2 Desktop Shell
    React + TypeScript + Vite Cockpit
                  │
                  ▼ (Local REST & Ephemeral Credentials)
       Local FastAPI Backend (Port 8000)
    Authentication │ Validation │ Budget Limits
    Approval Queue │ Audit Log  │ Tool Policies
                  │
         ┌────────┴────────┐
         ▼                 ▼
   OpenAI Realtime    Local SQLite Engine
   (WebRTC direct)    (Tasks, Memories, Audit)
```

- **Desktop Shell & Cockpit**: Tauri 2 + React 19 + TypeScript + Vite (`desktop/`)
  - **`AssistantOrb`**: High-performance visual core supporting 6 operational states (`idle`, `listening`, `thinking`, `speaking`, `disconnected`, `error`) with dynamic audio reactivity.
  - **`VoiceControls`**: Push-to-talk toggle, microphone mute, real-time audio VU equalizer, live session duration timer, and emergency disconnect.
  - **`ConversationPanel`**: Live transcript stream with tool execution badges and typed fallback input.
  - **`TaskPanel`**: Task lifecycle management with status/priority filtering, due-date tracking, and imminent reminder alerts.
  - **`MemoryPanel`**: Categorized structured memories (`preference`, `project`, `knowledge`, `task_history`) and path-safe local document keyword search.
  - **`ApprovalDialog`**: Gated authorization modal displaying exact action parameters, countdown expiration timers, execute/reject buttons, and audit trail viewer.
  - **`SettingsPanel`**: Daily API budget progress bar, spending cap modifier, voice persona selector, and sandboxed directory manager.
- **Backend Service**: Python 3.12 + FastAPI + Pydantic Settings (`backend/`)
  - Secret-masking logger (`SecretMaskingFilter`) protecting credentials from logs.
  - Ephemeral OpenAI Realtime session token minting (`POST /api/voice/session`) ensuring `OPENAI_API_KEY` never reaches client code.
  - Typed Tool Registry formatting JSON schemas for OpenAI Realtime function calling.
  - Security Policy Engine enforcing automatic vs. explicit-confirmation vs. blocked tool classification.
- **Persistence & Migration**: SQLite with SQLAlchemy 2.0 declarative models and Alembic migrations:
  - `tasks`: Daily tasks and scheduled reminders.
  - `memories`: User-approved long-term memory records.
  - `user_settings`: Application settings, daily budget limits, and spend metrics.
  - `approvals`: Cryptographically unique, 5-minute time-bounded action tokens.
  - `audit_events`: Immutable audit trail of every tool call and security decision.

---

## 2. Quickstart on Windows 11

### One-Click Launch

To launch both the FastAPI backend and Desktop Cockpit in parallel:

```cmd
start_jarvis.bat
```

Or start components individually:

- **Backend only:** `start_backend.bat`
- **Desktop Cockpit only:** `start_desktop.bat`

### End-to-End System Quality Verification

To run all automated lint checks, backend tests, frontend tests, strict typechecks, and production bundle builds in one command:

```cmd
verify_system.bat
```

---

## 3. Manual Setup & Verification

### Prerequisites

- **Python**: 3.12+ (or 3.11+)
- **Node.js**: v22 LTS and npm
- **Rust & Cargo**: 1.90+ with MSVC toolchain (`stable-x86_64-pc-windows-msvc`)
- **Visual Studio Build Tools**: "Desktop development with C++" workload (for MSVC linker `link.exe` and Windows SDK)
- **Microsoft Edge WebView2**: Runtime installed (included by default on Windows 11)

### Backend Setup

```cmd
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
copy .env.example .env
alembic upgrade head
```

Run tests and linter:

```cmd
python -m pytest -v
ruff check app tests
```

Start backend development server:

```cmd
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Endpoints:
- Health check: `http://127.0.0.1:8000/api/health`
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`

### Frontend Setup

```cmd
cd desktop
npm install
```

Run unit tests, strict typecheck, and production build:

```cmd
npm test
npm run typecheck
npm run build
```

Run web cockpit in development:

```cmd
npm run dev
```

Run native desktop application via Tauri (requires Visual Studio C++ Build Tools):

```cmd
npm run tauri dev
```

---

## 4. Security & Safety Model

1. **Zero Client-Side Secret Exposure:** The permanent `OPENAI_API_KEY` is strictly confined to `backend/.env`. The desktop frontend communicates using temporary ephemeral tokens (`ek_...`) generated on-demand by `POST /api/voice/session`.
2. **Approval-First Execution:** Destructive actions (such as `delete_file`) cannot run autonomously. They generate a time-bounded approval token (5-minute expiry) and require explicit user authorization before execution.
3. **Execution Integrity:** Parameters cannot be tampered with between authorization and execution. Arguments are re-validated immediately before the tool handler runs.
4. **Sandboxed File Operations:** Document searching (`MemoryService.search_allowed_documents`) and file actions are strictly constrained to canonical directories listed in `JARVIS_ALLOWED_DIRS`. Path-traversal attempts (e.g. `../../Windows`) are blocked and audited.
5. **Prohibited Commands:** Arbitrary shell interpreters (`cmd.exe`, `powershell`, `bash`) and destructive system commands are blocked by default.
6. **API Budget Safeguards:** Daily API expenditure is tracked in SQLite. If `JARVIS_MAX_DAILY_API_BUDGET_USD` is reached, `POST /api/voice/session` returns `HTTP 429` (`BUDGET_EXCEEDED`), halting new session creation.
7. **Tamper-Evident Audit Trail:** Every action attempt—whether executed, denied, approved, rejected, or expired—is logged immutably with timestamp and parameters to the `audit_events` table.

---

## 5. Automated Verification Checklist

All items from the implementation blueprint have been verified by automated tests:

### Setup & Reliability
- [x] Backend starts and `/api/health` responds with status, service, and version.
- [x] Desktop launches and connects to backend with visual status indicator.
- [x] App handles backend and network outages gracefully with offline alerts.
- [x] Settings, tasks, and memory persist across restarts in SQLite.

### Voice & WebRTC
- [x] Microphone permission requested and audio tracks managed cleanly.
- [x] Ephemeral session credentials minted without exposing server API key.
- [x] Interruption controls allow user to halt assistant playback.
- [x] Disconnect closes audio tracks, analyzer contexts, and session resources.
- [x] Expired or lost connections trigger bounded exponential backoff reconnection.

### Memory & Tasks
- [x] Structured memories persist across restarts with categorization.
- [x] Memories can be filtered, inspected, updated, and deleted.
- [x] Tasks are created, queried, marked complete, and rescheduled.
- [x] Proactive due reminders query returns imminent tasks.
- [x] Malformed requests and invalid ISO dates are rejected with 422 Unprocessable Entity.
- [x] Sensitive tokens and API keys are masked by logger filters.

### Security & Approvals
- [x] Permanent API key is absent from frontend bundles and network payloads.
- [x] Arbitrary shell execution is blocked with 403 Forbidden.
- [x] Path traversal attempts outside allowed folders are rejected.
- [x] Consequential actions queue time-bounded approval requests.
- [x] Expired and duplicate approvals are rejected.
- [x] Approved actions execute handler; rejected actions abort execution.

### Budget & UI
- [x] Daily API spending limit blocks new sessions when reached.
- [x] Active session duration and cumulative voice seconds are tracked.
- [x] AssistantOrb displays all 6 operational states.
- [x] Accessible keyboard focus, labels, and responsive layout.
- [x] Production bundle builds successfully without dev server.

---

## 6. Implementation Milestones

- **Milestone 1:** Application Foundation & Shell — *Verified*
- **Milestone 2:** Cockpit UI & Persistence — *Verified*
- **Milestone 3:** Voice Session & WebRTC Integration — *Verified*
- **Milestone 4:** Tasks & Reminders — *Verified*
- **Milestone 5:** Structured Memory & Local Retrieval — *Verified*
- **Milestone 6:** Typed Tool Registry, Approvals & Audit Logging — *Verified*
- **Milestone 7:** Budget Safeguards, Error Recovery & Reconnect — *Verified*
- **Milestone 8:** Packaging, Verification & Operational Readiness — *Verified*

---

## 7. Test Suite Summary

- **Backend Tests (`pytest`):** 44 passed, 0 failed
- **Frontend Tests (`vitest`):** 44 passed across 9 test files, 0 failed
- **Total Automated Tests:** **88 passed**
- **Linters (`ruff`, `oxlint`):** 0 errors
- **TypeScript (`tsc -b`):** 0 errors
- **Production Build (`vite build`):** Succeeded into `desktop/dist/`
