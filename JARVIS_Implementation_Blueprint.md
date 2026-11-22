# JARVIS — Detailed Implementation Blueprint

**Project:** JARVIS Personal AI Desktop Assistant  
**Platform:** Windows 11  
**Hardware target:** 16 GB RAM, Intel integrated graphics, no dedicated GPU  
**Stack:** Python + FastAPI, OpenAI Realtime API, React + TypeScript + Vite, Tauri 2, SQLite  
**Operating approach:** Hybrid cloud reasoning with local memory, approval-first computer automation, low-cost API usage

---

## 1. Project vision

Build a real, locally installed personal AI assistant inspired by JARVIS from Iron Man. It should converse naturally, remember approved information, help manage daily tasks, search selected local documents, and perform carefully controlled computer actions.

Do not build only a mockup or a chatbot inside a futuristic interface. Implement the app incrementally, run tests, fix errors, and document anything that still requires credentials or manual setup.

### MVP capabilities

- Natural spoken conversation using the OpenAI Realtime API.
- Push-to-talk initially, with a wake-word adapter as an optional later feature.
- Spoken and typed interaction.
- Persistent, user-controlled memory for preferences, projects, and tasks.
- Create, list, complete, and reschedule tasks.
- Local document search and selected-file summarization.
- Open approved applications and search approved folders.
- A polished desktop interface with listening, thinking, speaking, disconnected, and error states.
- An approval workflow for consequential actions.
- Usage estimates, API budget safeguards, action logs, and honest error reporting.

### Out of scope for the first version

- Unrestricted shell access.
- Unrestricted filesystem access.
- Autonomous email sending, purchasing, payments, or account changes.
- Always-on recording or surveillance.
- Large local language models requiring substantial GPU resources.
- Complex 3D rendering.

Build a dependable assistant first. Add more autonomy only after the core system is reliable and tested.

---

## 2. Technology stack

### Desktop frontend
- React
- TypeScript with strict mode
- Vite
- Tauri 2
- CSS/SVG for lightweight animations
- `lucide-react` for icons
- WebRTC for Realtime voice sessions

### Backend
- Python
- FastAPI
- Pydantic Settings
- SQLAlchemy
- Alembic
- SQLite
- HTTPX
- Pytest and pytest-asyncio
- Ruff

### AI and voice
- OpenAI Realtime API for low-latency speech-to-speech.
- Short-lived Realtime client credentials created by the backend.
- Configurable model and voice settings.
- Model-independent service interfaces so the reasoning provider can be changed without rewriting the app.

### Memory
- SQLite for structured memories, tasks, preferences, approvals, settings, and audit records.
- Local document retrieval, initially using keyword search.
- Optional vector search later using ChromaDB or another suitable vector store.

### Hardware considerations
The target laptop has 16 GB RAM and integrated graphics. Prefer cloud reasoning for demanding AI tasks. Keep local services lightweight and avoid running large models by default. CSS, SVG, and small canvas effects are sufficient for a polished interface.

---

## 3. System architecture

The local backend is the trusted control center. The frontend must never contain the permanent OpenAI API key.

```text
User: Voice / Text / Optional Screenshot
                  |
                  v
       Tauri Desktop Application
       React + TypeScript + WebRTC
                  |
                  v
       Local FastAPI Backend
 Authentication | Validation | Limits
 Approval Queue | Audit | Tool Policies
                  |
          +-------+-------+
          |               |
          v               v
   Cloud AI Services   Local Services
   Realtime Voice      SQLite Database
   Reasoning/Tools     Local Documents
          |             Task Management
          +-------+-------+
                  |
                  v
       Permission-Controlled Actions
       Validate -> Approve -> Execute
                -> Verify -> Log
```

### Voice session flow

1. The user presses the microphone button.
2. The frontend requests a short-lived Realtime client credential from FastAPI.
3. FastAPI uses the permanent API key on the server side to create the session credential using the current official API flow.
4. The frontend establishes a WebRTC connection to the Realtime API.
5. JARVIS receives and responds to speech.
6. When a tool call is requested, the application routes it through the backend's typed tool registry.
7. The backend validates the request and checks its permission policy.
8. If required, the backend creates an approval item.
9. Only an authorized action is executed. The result is returned to the model and UI.

Never allow a model-generated tool call to execute directly in the operating system.

---

## 4. Repository and folder structure

Use one repository with separate backend and desktop directories.

```text
jarvis/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── health.py
│   │   │       ├── voice.py
│   │   │       ├── tasks.py
│   │   │       ├── memory.py
│   │   │       └── approvals.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── realtime_service.py
│   │   │   ├── memory_service.py
│   │   │   ├── task_service.py
│   │   │   ├── action_service.py
│   │   │   └── audit_service.py
│   │   └── tools/
│   │       ├── registry.py
│   │       ├── policies.py
│   │       └── handlers.py
│   ├── tests/
│   ├── .env
│   ├── .env.example
│   └── pyproject.toml
├── desktop/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AssistantOrb.tsx
│   │   │   ├── VoiceControls.tsx
│   │   │   ├── ConversationPanel.tsx
│   │   │   ├── ApprovalDialog.tsx
│   │   │   ├── TaskPanel.tsx
│   │   │   └── MemoryPanel.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   └── Settings.tsx
│   │   ├── hooks/
│   │   │   └── useRealtime.ts
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   └── realtime.ts
│   │   ├── store/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── src-tauri/
│   │   ├── tauri.conf.json
│   │   └── capabilities/
│   └── package.json
├── shared-docs/
├── README.md
└── .gitignore
```

Keep SQLite databases, logs, personal documents, virtual environments, build artifacts, and secrets out of Git. Store persistent application data in the user's application data directory rather than in the source repository.

---

## 5. Windows 11 prerequisites

Install:

- Python 3.12 or another Python version supported by the chosen dependencies.
- Node.js LTS.
- Git for Windows.
- Rust using rustup with the stable MSVC toolchain.
- Visual Studio Build Tools with **Desktop development with C++**.
- Microsoft Edge WebView2 Runtime.

Tauri's official Windows setup documentation should be treated as the source of truth for current prerequisites.

Check installations in CMD:

```bat
python --version
node -v
npm -v
git --version
rustc --version
cargo --version
```

Restart the terminal after installing Rust or changing PATH.

---

## 6. Create the repository

Use the F: drive if desired to reduce pressure on the C: drive.

```bat
F:
mkdir Projects
cd Projects
mkdir jarvis
cd jarvis
git init
mkdir backend
```

If `F:\Projects` already exists, do not create it again; simply navigate to it.

---

## 7. Set up the Python backend

```bat
cd F:\Projects\jarvis\backend
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" pydantic-settings openai sqlalchemy alembic aiosqlite httpx python-multipart
pip install pytest pytest-asyncio ruff
mkdir app
cd app
mkdir api core db schemas services tools
cd ..
mkdir tests
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="JARVIS API", version="0.1.0")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "jarvis"}
```

Run the backend:

```bat
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify:
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/docs`

Stop the server with `Ctrl+C` before switching to other setup tasks.

---

## 8. Set up React + Tauri

Open a second CMD window:

```bat
F:
cd \Projects\jarvis
npm create vite@latest desktop -- --template react-ts
cd desktop
npm install
npm install lucide-react
npm install -D @tauri-apps/cli
npx tauri init
```

During Tauri initialization, configure the Vite development server and build settings to match the generated project. For a standard Vite project, the typical values are:

- Development URL: `http://localhost:5173`
- Frontend build directory: `../dist`
- Before development command: `npm run dev`
- Before build command: `npm run build`

Run the desktop app:

```bat
npm run tauri dev
```

If a Rust or Windows build error occurs, fix the prerequisite or compiler error before adding application features.

---

## 9. Environment variables

Create `backend/.env.example`:

```dotenv
APP_NAME=JARVIS
APP_ENV=development
HOST=127.0.0.1
PORT=8000

OPENAI_API_KEY=
OPENAI_REALTIME_MODEL=gpt-realtime-mini
OPENAI_REALTIME_VOICE=marin

DATABASE_URL=sqlite:///./jarvis.db
JARVIS_DATA_DIR=
JARVIS_ALLOWED_DIRS=
JARVIS_MAX_DAILY_API_BUDGET_USD=1.00

FRONTEND_ORIGIN=http://localhost:5173
LOG_LEVEL=INFO
```

These model and voice values are examples, not a guarantee that every identifier is enabled for the API account. Verify current supported Realtime models, voices, and session-credential creation steps in official OpenAI API documentation before implementation. Keep these values configurable.

Copy the template:

```bat
cd F:\Projects\jarvis\backend
copy .env.example .env
```

Edit `.env` and enter the API key locally. Never commit the real `.env` file or place the permanent key in frontend code, frontend environment variables, logs, screenshots, or prompts.

Use Pydantic Settings to validate configuration at startup. Fail with a clear error if a required value is missing.

### API cost safeguards

- Configure a small account budget and provider usage alerts.
- Use the least expensive suitable Realtime model available to the account.
- Limit session duration and concurrent sessions.
- Close sessions on disconnect and idle timeout.
- Track estimated usage locally.
- Stop starting new sessions after the configured application-level daily limit.
- Reconcile estimates against actual provider usage.
- Explain that a local counter is not an authoritative billing limit.

The example `$1.00` is an application-level development safeguard, not a guaranteed provider-enforced cap.

---

## 10. Backend implementation order

### Milestone 1: Application foundation
Implement:
- Configuration and validation.
- FastAPI application factory or entry point.
- Health endpoint.
- Structured error responses.
- Logging that excludes secrets.
- Basic tests.

Completion criteria: the backend starts and rejects invalid configuration cleanly.

### Milestone 2: Local persistence
Create SQLAlchemy models and Alembic migrations for:
- Tasks.
- Memories.
- User settings.
- Approvals.
- Audit events.

Completion criteria: data persists after restart and migrations work.

### Milestone 3: Realtime voice service
Implement `POST /api/voice/session`:
- Authenticate to OpenAI on the backend.
- Create short-lived Realtime client credentials using the current documented API.
- Return only the temporary credential and required session metadata.
- Never return the permanent API key.
- Apply model configuration, duration limits and error handling.

Completion criteria: the frontend can establish a Realtime session without exposing the permanent key.

### Milestone 4: Tasks and reminders
Implement:
- Create task.
- List tasks.
- Update due date or status.
- Complete task.
- Delete task if needed, with appropriate safeguards.
- Basic local reminders while the application is running.

Completion criteria: task changes persist and display correctly.

### Milestone 5: Memory
Separate:
- Explicit preferences.
- Project context.
- Task history.
- Searchable document knowledge.

Allow the user to inspect, edit and delete memories. Do not automatically save every conversation permanently.

Completion criteria: relevant approved memory can be retrieved across restarts.

### Milestone 6: Tool registry and approvals
Create typed, server-defined tool handlers and permission policies. Validate arguments and scope before execution.

Completion criteria: model tool calls cannot bypass authorization or execute arbitrary commands.

### Milestone 7: Audit, recovery and budget
Implement:
- Action IDs and outcomes.
- Timeouts and bounded retries.
- Duplicate-request protection.
- Session usage estimates.
- Budget safeguards.
- Clear error reporting.

Completion criteria: failures and action results can be inspected and explained.

---

## 11. API contract

Implement these endpoints with Pydantic request and response schemas and appropriate status codes.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Backend status |
| POST | `/api/voice/session` | Create a short-lived voice session credential |
| GET | `/api/tasks` | List tasks |
| POST | `/api/tasks` | Create a task |
| PATCH | `/api/tasks/{id}` | Update task status or due date |
| GET | `/api/memory` | List saved memories |
| POST | `/api/memory` | Save an explicitly approved memory |
| DELETE | `/api/memory/{id}` | Delete a saved memory |
| GET | `/api/approvals` | List pending actions |
| POST | `/api/approvals/{id}/approve` | Approve a pending action |
| POST | `/api/approvals/{id}/reject` | Reject a pending action |

Keep database access in the backend. The frontend must not directly open SQLite files or execute shell commands.

---

## 12. Tool execution and approval-first security

The model may request a tool operation but must never execute it directly. The backend validates every request against a server-defined registry and policy.

### Initial allowlisted tools

- `create_task`
- `list_tasks`
- `complete_task`
- `search_allowed_files`
- `read_allowed_text_file`
- `open_allowed_application`
- `search_local_memory`

### Initial action policies

| Action | Policy |
|---|---|
| Answer a question | Automatic |
| Search approved local notes | Automatic |
| Create a task | Automatic or configurable |
| Open an approved application | Automatic or configurable |
| Read a file in an approved folder | Automatic, with scope checks |
| Delete or overwrite files | Explicit confirmation |
| Run terminal commands | Explicit confirmation and command validation |
| Send email or submit a form | Explicit confirmation |
| Purchase, pay, or change account settings | Explicit confirmation |

### Approval requirements

- Bind approval to the exact action, arguments and expiry.
- If the action or arguments change, invalidate the approval.
- Reject expired and duplicate approval requests.
- Revalidate permissions immediately before execution.
- Prevent path traversal and access outside approved directories.
- Log the action attempt and outcome.
- Never provide a generic unrestricted shell or filesystem tool to the model.
- Keep a visible stop/disconnect control.

---

## 13. Memory design

Use SQLite as the authoritative local store for:
- Explicit preferences.
- Approved memories.
- Tasks and due dates.
- Application settings.
- Pending approvals.
- Audit events.

For personal knowledge:
1. Start with user-selected local documents.
2. Add keyword search.
3. Add vector retrieval only if it materially improves results.
4. Send only the minimum relevant context to the cloud model.
5. Ask for permission before sending sensitive material to cloud services.

For example, if the user asks to continue a project, retrieve the relevant project notes and recent decisions rather than uploading the entire document collection.

---

## 14. Frontend implementation order

Build a polished, dark navy interface with restrained cyan highlights, subtle glass effects and lightweight motion.

### Component order

1. `AssistantOrb.tsx`
   - Idle, listening, thinking, speaking, error and disconnected states.
2. `VoiceControls.tsx`
   - Microphone permissions, connection state, mute and disconnect.
3. `ConversationPanel.tsx`
   - User and assistant messages, timestamps and tool activity.
4. `TaskPanel.tsx`
   - Today's tasks, due dates and completion controls.
5. `ApprovalDialog.tsx`
   - Exact action details, arguments, approve and reject buttons.
6. `MemoryPanel.tsx`
   - Inspect, edit and delete saved memories.
7. `Settings.tsx`
   - Voice settings, connection status, budget safeguards and allowed folders.

### Realtime hook

Create `useRealtime.ts` to own the WebRTC connection lifecycle:
- Request a short-lived credential from FastAPI.
- Create and clean up the peer connection.
- Request microphone permission only when the user starts voice mode.
- Play the returned audio stream.
- Receive events and update UI state.
- Support interruption and disconnection.
- Handle network loss, expired sessions and reconnect attempts.
- Close microphone tracks and release resources on disconnect.

Use WebRTC instead of implementing a custom audio transport. Follow the current official Realtime API documentation.

### UI rules
- Do not block the interface during network requests.
- Show useful loading and error states.
- Provide a typed-input fallback if voice is unavailable.
- Use accessible keyboard focus and labels.
- Keep animations lightweight.
- Do not claim an action succeeded until the backend confirms the result.

---

## 15. Automated testing

Run these backend checks:

```bat
cd F:\Projects\jarvis\backend
python -m pytest -q
ruff check app tests
```

For the frontend, add Vitest and React Testing Library. Then run the project's actual scripts, including:

```bat
cd F:\Projects\jarvis\desktop
npm run build
npm run tauri dev
```

Do not assume test scripts exist until they have been configured in `package.json`.

### Required test checklist

#### Setup and reliability
- [ ] Backend starts and health endpoint responds.
- [ ] Desktop launches and connects to backend.
- [ ] App handles backend and internet outages.
- [ ] Settings and database persist after restart.

#### Voice
- [ ] Microphone permission is requested correctly.
- [ ] Realtime session connects and produces audio.
- [ ] User can interrupt an assistant response.
- [ ] Disconnect closes audio tracks and session resources.
- [ ] Expired credentials trigger safe reconnection.

#### Memory and tasks
- [ ] Approved memory persists across restart.
- [ ] Memory can be inspected and deleted.
- [ ] Tasks are saved, updated and completed correctly.
- [ ] Invalid dates and malformed requests are rejected.
- [ ] Sensitive data is not logged accidentally.

#### Security and approvals
- [ ] Permanent API key is absent from frontend bundles.
- [ ] Model cannot directly execute shell commands.
- [ ] File access outside approved directories is denied.
- [ ] Changing approved arguments invalidates approval.
- [ ] Expired and duplicate approval requests are rejected.
- [ ] Destructive actions require explicit approval.

#### Budget and UI
- [ ] Daily budget safeguard blocks new sessions when reached.
- [ ] Session duration and usage are tracked.
- [ ] Listening, speaking, loading and error states work.
- [ ] Buttons remain usable at smaller window sizes.
- [ ] Production build works without the development server.

Mock paid API calls during unit tests. Never require live API credits to run the test suite. Mark a checklist item complete only after it has actually been tested.

---

## 16. `.gitignore`

At minimum, exclude:

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
node_modules/
dist/
target/
*.db
*.sqlite
*.sqlite3
logs/
*.log
```

Review Tauri build output paths and any generated credentials or local data paths to ensure they are excluded as well.

---

## 17. Suggested implementation schedule

These are planning estimates, not guaranteed deadlines.

- **Day 1:** Repository, configuration, FastAPI health endpoint and Tauri shell.
- **Days 2–3:** Realtime session setup and voice conversation.
- **Days 4–5:** SQLite persistence, tasks and memory.
- **Days 6–7:** Typed tools, approval workflow and audit logs.
- **Week 2 onward:** Automated testing, packaging, cost tuning and additional integrations.

Prioritize a complete, tested slice over a large collection of unfinished features.

---

## 18. Antigravity IDE execution instructions

Act as a senior AI systems architect, Python backend engineer, React/TypeScript engineer, Tauri desktop developer, voice-agent engineer and application security engineer.

### Required workflow

1. Inspect the existing workspace and installed dependencies before changing anything.
2. Preserve existing user files and working code.
3. Present a concise implementation plan.
4. Create the folder structure and configuration templates.
5. Implement **Milestone 1 only**.
6. Run the relevant tests and build checks.
7. Fix errors rather than suppressing them.
8. Report the exact commands run and their actual results.
9. Continue to the next milestone only after the current milestone works.
10. Never fabricate successful tests or claim an untested integration works.

Use Windows CMD-compatible commands in documentation. Do not require Docker for the initial MVP. Do not install a local LLM unless a later, explicit feature requires it.

Use official OpenAI Realtime API documentation to verify supported models, client-secret creation, WebRTC connection steps, events and tool-call behavior. Use official Tauri 2 documentation for Windows prerequisites and capabilities.

### Completion criteria

The MVP is complete only when:
- The Tauri application launches.
- The backend health check succeeds.
- A configured Realtime session can connect and exchange audio.
- Tasks persist across restarts.
- Approved memories can be retrieved and deleted.
- Consequential actions require explicit approval.
- Rejected actions do not execute.
- API credentials remain server-side.
- The application reports failures honestly.
- Automated tests pass and the production frontend builds successfully.

If credentials, hardware dependencies or unsupported API features block a test, explain the blocker precisely and provide a reproducible manual test.

**Begin by inspecting the workspace and implementing Milestone 1. Do not attempt to build every feature in one unverified pass.**

---

## 19. Official documentation

Use current official documentation as the implementation source of truth. API models, endpoints, and configuration options may change.

- OpenAI API documentation: https://platform.openai.com/docs/
- OpenAI Realtime API guide: https://platform.openai.com/docs/guides/realtime
- OpenAI API reference: https://platform.openai.com/docs/api-reference/realtime
- FastAPI documentation: https://fastapi.tiangolo.com/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Tauri 2 documentation: https://v2.tauri.app/
- Tauri prerequisites: https://v2.tauri.app/start/prerequisites/
- Vite documentation: https://vite.dev/
- SQLAlchemy documentation: https://docs.sqlalchemy.org/
- Alembic documentation: https://alembic.sqlalchemy.org/

---

## Final engineering principle

Make JARVIS reliable before making it autonomous. A voice assistant that remembers useful information, manages tasks and safely operates a few tools is already valuable. Unrestricted access to the computer is not a feature; it is a security incident waiting for a misunderstood sentence.
