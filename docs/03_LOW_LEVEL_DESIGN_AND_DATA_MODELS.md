# JARVIS — Low-Level Design & Data Models (LLD)

**Document Version:** 1.0.0  
**Status:** Approved / Base-Lined  
**Classification:** Technical Implementation Specification  

---

## 1. Database Schema Specification

The storage engine utilizes SQLite via SQLAlchemy ORM models. All tables utilize UUID primary keys formatted as 32-character hexadecimal strings or standard hyphenated UUIDv4 strings.

### 1.1 Table: `tasks`
Stores actionable user tasks, deadlines, and automated reminder triggers.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | Unique task identifier (UUIDv4) |
| `title` | `VARCHAR(255)` | `NOT NULL` | Short title of the task |
| `description` | `TEXT` | `NULLABLE` | Detailed notes or context |
| `status` | `VARCHAR(32)` | `NOT NULL, DEFAULT 'pending'` | Enum: `pending`, `in_progress`, `completed`, `cancelled` |
| `priority` | `VARCHAR(32)` | `NOT NULL, DEFAULT 'medium'` | Enum: `low`, `medium`, `high`, `urgent` |
| `deadline` | `DATETIME` | `NULLABLE` | Target completion timestamp (UTC) |
| `reminder_time` | `DATETIME` | `NULLABLE` | Notification trigger timestamp (UTC) |
| `created_at` | `DATETIME` | `NOT NULL, DEFAULT utcnow` | Record insertion timestamp |
| `updated_at` | `DATETIME` | `NOT NULL, DEFAULT utcnow` | Last update timestamp |

**Indexes:**
- `ix_tasks_status` on `tasks(status)`
- `ix_tasks_priority` on `tasks(priority)`
- `ix_tasks_reminder_time` on `tasks(reminder_time)`

---

### 1.2 Table: `memories`
Stores persistent user preferences, system configurations, facts, and workflow definitions.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | Unique memory identifier (UUIDv4) |
| `content` | `TEXT` | `NOT NULL` | Memory text / knowledge payload |
| `category` | `VARCHAR(64)` | `NOT NULL, DEFAULT 'fact'` | Enum: `preference`, `fact`, `workflow`, `system` |
| `tags` | `VARCHAR(255)` | `NULLABLE` | Comma-separated search and categorization tags |
| `created_at` | `DATETIME` | `NOT NULL, DEFAULT utcnow` | Record insertion timestamp |
| `updated_at` | `DATETIME` | `NOT NULL, DEFAULT utcnow` | Last update timestamp |

**Indexes:**
- `ix_memories_category` on `memories(category)`

---

### 1.3 Table: `approvals`
Tracks Human-in-the-Loop approval requests, execution decisions, and security audit logs.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `id` | `VARCHAR(36)` | `PRIMARY KEY` | Unique approval identifier (UUIDv4) |
| `action_type` | `VARCHAR(64)` | `NOT NULL` | Tool or function name (e.g., `write_file`) |
| `parameters` | `TEXT` | `NOT NULL` | JSON serialized arguments dictionary |
| `risk_level` | `VARCHAR(32)` | `NOT NULL` | Enum: `low`, `medium`, `high` |
| `status` | `VARCHAR(32)` | `NOT NULL, DEFAULT 'pending'` | Enum: `pending`, `approved`, `rejected` |
| `requested_at`| `DATETIME` | `NOT NULL, DEFAULT utcnow` | Action submission timestamp |
| `resolved_at` | `DATETIME` | `NULLABLE` | User decision timestamp |
| `resolved_by` | `VARCHAR(64)` | `NULLABLE` | Identifier of decider (`user`, `policy_engine`) |

**Indexes:**
- `ix_approvals_status` on `approvals(status)`
- `ix_approvals_action_type` on `approvals(action_type)`

---

### 1.4 Table: `user_settings`
Key-value store maintaining operational state, daily budget caps, session metrics, and preferences.

| Column | Type | Constraints | Description |
|:---|:---|:---|:---|
| `key` | `VARCHAR(128)` | `PRIMARY KEY` | Setting identifier key |
| `value` | `TEXT` | `NOT NULL` | Setting value string or serialized JSON |
| `updated_at` | `DATETIME` | `NOT NULL, DEFAULT utcnow` | Modification timestamp |

**Key Dictionary:**
- `budget_date`: Date string (`YYYY-MM-DD`) tracking the current budget window.
- `budget_custom_limit_usd`: User-configured daily spending limit in USD.
- `budget_spent_usd`: Accumulated estimated expenditure for today.
- `budget_sessions_today`: Cumulative count of voice sessions initiated today.
- `budget_duration_seconds_today`: Cumulative seconds of voice streaming today.
- `budget_active_sessions`: Current concurrent active voice sessions counter.

---

## 2. REST API Endpoint Specifications

### 2.1 System & Voice Endpoints

#### `GET /api/health`
Returns system operational status, service name, and version.
- **Response:** `200 OK`
  ```json
  {
    "status": "ok",
    "service": "jarvis",
    "version": "0.1.0"
  }
  ```

#### `POST /api/voice/session`
Initializes voice session credentials according to active `AI_PROVIDER`.
- **Request Body (optional):**
  ```json
  {
    "model": "gemini-2.0-flash",
    "voice": "Puck"
  }
  ```
- **Response:** `201 Created`
  ```json
  {
    "provider": "gemini",
    "client_secret": "",
    "ws_url": "/api/voice/gemini-live",
    "expires_at": 1792164449,
    "session_id": "gemini-2d6f8ab29bc1",
    "model": "gemini-2.0-flash",
    "voice": "Puck"
  }
  ```
- **Error Responses:** `429 Too Many Requests` (budget exceeded), `500 Internal Server Error` (missing API keys).

#### `WebSocket /api/voice/gemini-live`
Bidirectional WebSocket audio streaming bridge directly proxying messages to Google Gemini Multimodal Live API.

---

### 2.2 Task Management Endpoints

#### `GET /api/tasks`
Lists stored tasks with optional status and priority query filters.
- **Query Parameters:** `status` (string), `priority` (string), `limit` (int, default 50).
- **Response:** `200 OK`
  ```json
  {
    "tasks": [
      {
        "id": "c1f7a28e-8a10-410a-b3e1-d30f4e3c8120",
        "title": "Review security audit logs",
        "description": "Inspect high-risk actions executed today",
        "status": "pending",
        "priority": "high",
        "deadline": "2026-10-23T18:00:00Z",
        "reminder_time": "2026-10-23T17:00:00Z",
        "created_at": "2026-10-22T10:00:00Z",
        "updated_at": "2026-10-22T10:00:00Z"
      }
    ],
    "total": 1,
    "pending_count": 1,
    "completed_count": 0
  }
  ```

#### `POST /api/tasks`
Creates a new actionable task.
- **Request Body:**
  ```json
  {
    "title": "Clean temp files",
    "description": "Remove logs older than 7 days",
    "priority": "medium",
    "deadline": "2026-10-24T12:00:00Z"
  }
  ```
- **Response:** `201 Created` (returns created Task object).

#### `PATCH /api/tasks/{task_id}`
Updates task status, priority, or content.
- **Request Body:**
  ```json
  {
    "status": "completed"
  }
  ```
- **Response:** `200 OK` (returns updated Task object).

#### `DELETE /api/tasks/{task_id}`
Deletes a task by ID.
- **Response:** `200 OK` -> `{"deleted": true, "id": "..."}`.

#### `GET /api/tasks/reminders/due`
Returns all tasks whose reminder timestamp has expired and whose status is not completed.

---

### 2.3 Contextual Memory Endpoints

#### `GET /api/memory`
Lists stored memories filtered by category.
- **Query Parameters:** `category` (optional enum), `limit` (int, default 50).

#### `POST /api/memory`
Stores a new categorized memory.
- **Request Body:**
  ```json
  {
    "content": "User prefers dark mode and concise summaries",
    "category": "preference",
    "tags": "ui,formatting"
  }
  ```
- **Response:** `201 Created`.

#### `GET /api/memory/search`
Performs case-insensitive substring search across content and tags.
- **Query Parameters:** `q` (search term, required), `category` (optional).

#### `DELETE /api/memory/{memory_id}`
Removes a memory item.
- **Response:** `200 OK`.

---

### 2.4 Approvals & Audit Endpoints

#### `GET /api/approvals`
Lists pending or historical action requests.
- **Query Parameters:** `status` (default `pending`), `limit` (default 20).

#### `POST /api/approvals/{approval_id}/resolve`
Submits user approval or rejection for a gated action.
- **Request Body:**
  ```json
  {
    "approved": true,
    "reason": "Verified safe to execute"
  }
  ```
- **Response:** `200 OK` -> returns updated approval and execution result if approved.

#### `GET /api/approvals/audit`
Returns chronological audit log of all gated, executed, and rejected actions.

---

### 2.5 Budget & Settings Endpoints

#### `GET /api/budget/status`
Returns current day's API spend, remaining quota, active session count, and limit.
- **Response:** `200 OK`
  ```json
  {
    "date": "2026-10-22",
    "limit_usd": 1.00,
    "spent_usd": 0.24,
    "remaining_usd": 0.76,
    "is_budget_exceeded": false,
    "sessions_today": 12,
    "duration_seconds_today": 184,
    "active_sessions": 0
  }
  ```

#### `POST /api/budget/limit`
Sets user-defined daily budget limit.
- **Request Body:** `{"limit_usd": 2.50}`

#### `POST /api/budget/record-usage`
Records voice session duration and decrements active session counter.
- **Request Body:** `{"duration_seconds": 25, "estimated_cost": 0.025}`
- **Response:** `200 OK`

#### `POST /api/budget/reset`
Manually resets daily usage metrics to 0.0.

#### `GET /api/settings`
Returns operational configuration summary (environment, AI provider, audio rates, sandboxed directories).

---

## 3. Real-Time WebSocket Message Protocols

The WebSocket bridge adheres to event-driven message structures for both OpenAI DataChannel and Gemini WebSocket events:

### 3.1 Client-to-Server Messages

1. **`input_audio_buffer.append` (Microphone Chunk):**
   ```json
   {
     "type": "input_audio_buffer.append",
     "audio": "<base64_encoded_pcm16_16khz>"
   }
   ```
2. **`conversation.item.create` (Typed Text Prompt):**
   ```json
   {
     "type": "conversation.item.create",
     "text": "Open calculator and calculate total budget"
   }
   ```
3. **`response.cancel` (Interruption / Barge-in):**
   ```json
   {
     "type": "response.cancel"
   }
   ```

### 3.2 Server-to-Client Messages

1. **`session.created`:**
   ```json
   {
     "type": "session.created",
     "session": {
       "provider": "gemini",
       "model": "gemini-2.0-flash",
       "voice": "Puck"
     }
   }
   ```
2. **`response.audio.delta` (Model Voice Stream):**
   ```json
   {
     "type": "response.audio.delta",
     "delta": "<base64_encoded_pcm16_24khz>"
   }
   ```
3. **`response.audio_transcript.delta` (Speech Transcript):**
   ```json
   {
     "type": "response.audio_transcript.delta",
     "delta": "Opening calculator now..."
   }
   ```
4. **`response.function_call_arguments.done` (Tool Activity Notification):**
   ```json
   {
     "type": "response.function_call_arguments.done",
     "name": "launch_application",
     "arguments": "{\"app_name\": \"calc.exe\"}"
   }
   ```
5. **`response.done`:** Indicates assistant completion of utterance turn.

---

## 4. Tool Registry Specifications

| Function Name | Parameters Schema | Risk Level | Description |
|:---|:---|:---|:---|
| `get_system_status` | None | `LOW` | Queries CPU, RAM, disk space, and system uptime |
| `open_browser` | `url: string` (required) | `LOW` | Launches URL in default web browser |
| `list_directory` | `path: string` (default `.`) | `LOW` | Lists files within sandboxed directories |
| `read_file` | `path: string` (required) | `LOW` | Reads UTF-8 file content within sandboxed directories |
| `manage_task` | `action: string`, `title?: string`, `task_id?: string` | `MEDIUM` | Creates, completes, or updates user tasks |
| `manage_memory`| `action: string`, `content?: string`, `category?: string`| `MEDIUM` | Stores or retrieves long-term knowledge items |
| `launch_application`| `app_name: string`, `arguments?: string[]` | `MEDIUM` | Executes approved Windows desktop application |
| `write_file` | `path: string`, `content: string` | `HIGH` | Writes content to file within sandboxed directory |
| `execute_powershell`| `command: string` | `HIGH` | Executes PowerShell command (strict HITL approval required) |

---

## 5. Budget Calculation Engine Formulas

1. **Upfront Session Cost Withholding:**
   $$\text{Upfront Cost} = \$0.0100 \text{ USD}$$
   Withheld at session creation to account for initialization token handshake.

2. **Per-Second Streaming Cost Estimation:**
   $$\text{Streaming Cost} = \text{duration\_seconds} \times \$0.0010 \text{ USD}$$
   Calculated and billed incrementally when a session finishes.

3. **Concurrency Throttle & Self-Healing:**
   $$\text{Active Sessions Allowed} = 1 \text{ (Standard Desktop)}$$
   $$\text{Auto-Heal Trigger Threshold} = \ge 5 \text{ Active Sessions}$$
   When triggered, active session count is immediately normalized to 1, preventing lockouts from crashed browser tabs.
