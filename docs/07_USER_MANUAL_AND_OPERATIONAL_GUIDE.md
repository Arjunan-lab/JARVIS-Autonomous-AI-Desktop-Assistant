# JARVIS — User Manual & Operational Guide

**Document Version:** 1.0.0  
**Status:** Approved / Base-Lined  
**Classification:** End-User Operational Documentation  

---

## 1. Introducing JARVIS

JARVIS is your personal AI desktop assistant engineered specifically for Windows 11. Unlike conventional chatbots that run isolated inside a browser tab, JARVIS bridges high-speed real-time multimodal intelligence with your operating system:
- **Speaks and listens naturally** with sub-500ms voice turn latency.
- **Automates desktop tasks:** Launches applications, inspects system performance, reads/writes approved files, and schedules reminders.
- **Protects your security:** Every high-risk system command is intercepted and requires your explicit approval before execution.
- **Respects your budget:** Enforces strict daily spending limits so you never incur unexpected cloud reasoning fees.
- **Supports 100% Free Tier:** Operates seamlessly with free-tier Google Gemini Multimodal Live API (`gemini-2.0-flash`).

---

## 2. Cockpit Interface Overview

When you navigate to `http://localhost:5173/`, you are greeted by the tactical dark-themed JARVIS command cockpit:

```
+-----------------------------------------------------------------------------------+
|  [O] JARVIS   | Status: Backend Online | Provider: Gemini | Spent: $0.24 / $1.00  |
+-----------------------------------------------------------------------------------+
|  [Assistant Cockpit]  [Tasks & Reminders]  [Memory]  [Approvals (0)]  [Settings]   |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|                           ((((  ASSISTANT ORB  ))))                               |
|                                    [Idle]                                         |
|                                                                                   |
|                              [ Start Voice ]                                      |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Conversation Log                                                            |  |
|  | - JARVIS: Ready to assist you, Sir.                                         |  |
|  | - You: Open calculator and check CPU status                                 |  |
|  | - JARVIS: Launching calculator now. CPU load is currently 14%.              |  |
|  | [Type a message or instruction...                              ] [ Send ]   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

### 2.1 The Assistant Orb & Status States
The glowing central orb provides continuous visual feedback regarding the state of the voice pipeline:
- **Cyan Gentle Pulse (`idle`):** Assistant is standing by, ready for your input.
- **Expanding Reactive Waves (`listening`):** Assistant is actively listening to your voice. The orb pulses dynamically in sync with your vocal amplitude.
- **Rotating Shimmer (`processing`):** Assistant is reasoning, calling local tools, or waiting for cloud response.
- **Harmonic Purple/Cyan Waveform (`speaking`):** Assistant is streaming vocal audio through your speakers or headphones.

---

## 3. Operational Workflows

### 3.1 Initiating a Real-Time Voice Session
1. Click the cyan **"Start Voice"** button located directly beneath the central Orb.
2. If prompted by your browser, click **"Allow"** to grant microphone permissions.
3. Once connected, the button transforms into a red **"Stop Voice"** button, and the orb transitions to `idle` or `listening`.
4. Begin speaking naturally. Speak clearly into your microphone as you would to a colleague.
5. To end the voice session at any time, click **"Stop Voice"**.

### 3.2 Natural Interruption (Barge-in)
If JARVIS is speaking and you wish to cut in, simply speak. JARVIS will instantly halt its audio output, discard the remaining speech buffer, and listen to your new command.

### 3.3 Text-Based Conversation
If you prefer not to use your microphone:
1. Locate the **Conversation Log** at the bottom of the Assistant Cockpit.
2. Type your command into the text box (e.g., *"What tasks do I have scheduled for today?"*).
3. Press `Enter` or click the **Send** button.
4. JARVIS will process the prompt and reply in the conversation log.

---

## 4. Managing Tasks & Reminders

Click the **Tasks & Reminders** tab in the navigation bar:
- **Creating a Task via Voice:** Say *"Create a high priority task to review deployment logs before 6 PM."*
- **Creating a Task via UI:** Use the **"New Task"** card at the top of the panel. Enter the title, notes, priority (`Low`, `Medium`, `High`, `Urgent`), and optional deadline. Click **"Add Task"**.
- **Completing Tasks:** Click the checkbox next to any task to mark it `completed`. Completed tasks are archived automatically.
- **Due Reminders:** If a task has an active reminder timestamp that passes, an alert banner appears at the top of the screen.

---

## 5. Contextual Memory & Knowledge Store

Click the **Memory & Knowledge** tab to inspect what JARVIS remembers:
- **Categories:**
  - `Preference`: Your personal habits (e.g., preferred IDE, dark theme, favorite coding style).
  - `Fact`: Persistent facts (e.g., project URLs, server IP addresses, license keys).
  - `Workflow`: Instructions for recurring multi-step activities.
  - `System`: Hardware or local workstation details.
- **Teaching JARVIS via Voice:** Say *"Remember that my primary development branch is main."* JARVIS saves this into memory and references it during future voice sessions.
- **Searching Memories:** Type keywords in the search bar to locate specific entries instantly.

---

## 6. Security Approvals & Audit Trail

When JARVIS attempts to execute a high-risk operation (e.g., writing code to a file, executing PowerShell, or modifying system configurations), execution is **automatically halted**:
1. An **Approval Dialog** modal pops up in the UI.
2. Review the **Action Type** (e.g., `write_file`) and inspect the **Parameters** (e.g., target file path and code content).
3. **Decision:**
   - Click **"Approve"** if you trust the action. JARVIS executes the action immediately and reports the result.
   - Click **"Reject"** if the action is unintended or incorrect. JARVIS aborts the action safely and informs the model.
4. Navigate to **Approvals & Audit** tab to inspect the complete history of all past requests, timestamps, and decisions.

---

## 7. Budget & Safeguard Management

Click the **Settings & Budget** tab to manage cloud reasoning spend:
- **Daily Budget Cap:** Default is **$1.00 USD**. To adjust, enter a new dollar amount in the input field and click **"Update Limit"**.
- **Real-Time Spend Tracker:** Visual progress bar displays total dollars spent today, total voice sessions conducted, and total streaming duration.
- **Resetting Daily Spend:** Click **"Reset Daily Usage"** to clear today's spend counter back to $0.00.
- **Switching AI Providers:** Toggle between `gemini` (Free Tier) and `openai` (Realtime API).
