/**
 * JARVIS Desktop Backend API Client
 */

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: unknown[];
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: 'pending' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  pending_count: number;
  completed_count: number;
}

export interface CreateTaskPayload {
  title: string;
  description?: string;
  due_date?: string;
  priority?: 'low' | 'medium' | 'high';
}

export interface UpdateTaskPayload {
  title?: string;
  description?: string;
  due_date?: string | null;
  status?: 'pending' | 'completed' | 'cancelled';
  priority?: 'low' | 'medium' | 'high';
}

const BACKEND_URL = 'http://127.0.0.1:8000';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${BACKEND_URL}/api/health`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }

  return response.json();
}

export async function fetchTasks(filters?: {
  status?: string;
  priority?: string;
  due_today?: boolean;
}): Promise<TaskListResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.append('status', filters.status);
  if (filters?.priority) params.append('priority', filters.priority);
  if (filters?.due_today) params.append('due_today', 'true');

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${BACKEND_URL}/api/tasks${query}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch tasks: HTTP ${response.status}`);
  }

  return response.json();
}

export async function fetchDueReminders(): Promise<Task[]> {
  const response = await fetch(`${BACKEND_URL}/api/tasks/reminders`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch task reminders: HTTP ${response.status}`);
  }

  return response.json();
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  const response = await fetch(`${BACKEND_URL}/api/tasks`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to create task: HTTP ${response.status}`);
  }

  return response.json();
}

export async function updateTask(id: string, payload: UpdateTaskPayload): Promise<Task> {
  const response = await fetch(`${BACKEND_URL}/api/tasks/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to update task: HTTP ${response.status}`);
  }

  return response.json();
}

export async function deleteTask(id: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/tasks/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok && response.status !== 404) {
    throw new Error(`Failed to delete task: HTTP ${response.status}`);
  }
}

export type MemoryCategory = 'preference' | 'project' | 'knowledge' | 'task_history';

export interface Memory {
  id: string;
  category: MemoryCategory;
  content: string;
  approved: boolean;
  source: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  memories: Memory[];
  total: number;
  preference_count: number;
  project_count: number;
  knowledge_count: number;
  task_history_count: number;
}

export interface CreateMemoryPayload {
  category?: MemoryCategory;
  content: string;
  approved?: boolean;
  source?: string;
}

export interface UpdateMemoryPayload {
  category?: MemoryCategory;
  content?: string;
  approved?: boolean;
  source?: string;
}

export interface DocumentSearchResult {
  file_path: string;
  file_name: string;
  snippet: string;
  line_number?: number | null;
}

export interface MemorySearchResponse {
  query: string;
  memories: Memory[];
  documents: DocumentSearchResult[];
}

export async function fetchMemories(filters?: {
  category?: string;
  approved_only?: boolean;
  search?: string;
}): Promise<MemoryListResponse> {
  const params = new URLSearchParams();
  if (filters?.category) params.append('category', filters.category);
  if (filters?.approved_only) params.append('approved_only', 'true');
  if (filters?.search) params.append('search', filters.search);

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${BACKEND_URL}/api/memory${query}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch memories: HTTP ${response.status}`);
  }

  return response.json();
}

export async function createMemory(payload: CreateMemoryPayload): Promise<Memory> {
  const response = await fetch(`${BACKEND_URL}/api/memory`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to create memory: HTTP ${response.status}`);
  }

  return response.json();
}

export async function updateMemory(id: string, payload: UpdateMemoryPayload): Promise<Memory> {
  const response = await fetch(`${BACKEND_URL}/api/memory/${id}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Failed to update memory: HTTP ${response.status}`);
  }

  return response.json();
}

export async function deleteMemory(id: string): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/api/memory/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok && response.status !== 404) {
    throw new Error(`Failed to delete memory: HTTP ${response.status}`);
  }
}

export async function searchMemoryAndDocs(
  query: string,
  category?: string,
  searchDocs: boolean = true
): Promise<MemorySearchResponse> {
  const params = new URLSearchParams();
  params.append('q', query);
  if (category) params.append('category', category);
  if (!searchDocs) params.append('search_docs', 'false');

  const response = await fetch(`${BACKEND_URL}/api/memory/search?${params.toString()}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to search memory & docs: HTTP ${response.status}`);
  }

  return response.json();
}

export interface Approval {
  id: string;
  action_type: string;
  arguments: Record<string, unknown>;
  policy: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  expires_at: string;
  created_at: string;
  updated_at: string;
}

export interface ApprovalListResponse {
  approvals: Approval[];
  total: number;
  pending_count: number;
}

export interface ActionExecutionResponse {
  action_id?: string | null;
  action_type: string;
  status: 'executed' | 'requires_approval' | 'denied' | 'failed';
  result?: unknown;
  approval_id?: string | null;
  message?: string | null;
}

export interface AuditEvent {
  id: string;
  action_id?: string | null;
  action_type: string;
  outcome: string;
  details: Record<string, unknown>;
  timestamp: string;
}

export interface AuditListResponse {
  events: AuditEvent[];
  total: number;
}

export async function fetchApprovals(status?: string): Promise<ApprovalListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const response = await fetch(`${BACKEND_URL}/api/approvals${query}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch approvals: HTTP ${response.status}`);
  }

  return response.json();
}

export async function approveAction(
  approvalId: string
): Promise<{ approval_id: string; status: string; result?: unknown }> {
  const response = await fetch(`${BACKEND_URL}/api/approvals/${approvalId}/approve`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to approve action: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

export async function rejectAction(
  approvalId: string
): Promise<{ approval_id: string; status: string }> {
  const response = await fetch(`${BACKEND_URL}/api/approvals/${approvalId}/reject`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to reject action: HTTP ${response.status}`);
  }

  return response.json();
}

export async function requestAction(
  actionType: string,
  args: Record<string, unknown> = {}
): Promise<ActionExecutionResponse> {
  const response = await fetch(`${BACKEND_URL}/api/approvals/request`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ action_type: actionType, arguments: args }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to request action: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

export async function fetchAuditEvents(
  limit: number = 50,
  outcome?: string
): Promise<AuditListResponse> {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  if (outcome) params.append('outcome', outcome);

  const response = await fetch(`${BACKEND_URL}/api/approvals/audit?${params.toString()}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch audit events: HTTP ${response.status}`);
  }

  return response.json();
}

export interface BudgetStatus {
  date: string;
  limit_usd: number;
  spent_usd: number;
  remaining_usd: number;
  is_budget_exceeded: boolean;
  sessions_today: number;
  duration_seconds_today: number;
  active_sessions: number;
}

export interface AppSettings {
  app_name: string;
  app_env: string;
  ai_provider?: 'openai' | 'gemini';
  openai_model: string;
  openai_voice: string;
  gemini_model?: string;
  gemini_voice?: string;
  has_api_key: boolean;
  allowed_dirs: string[];
  max_daily_budget_usd: number;
}

export interface UpdateSettingsPayload {
  max_daily_budget_usd?: number;
  allowed_dirs?: string;
}

export async function fetchBudgetStatus(): Promise<BudgetStatus> {
  const response = await fetch(`${BACKEND_URL}/api/budget`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch budget status: HTTP ${response.status}`);
  }

  return response.json();
}

export async function recordSessionUsage(
  durationSeconds: number,
  estimatedCost?: number
): Promise<{ duration_seconds: number; added_cost_usd: number; total_spent_today: number }> {
  const response = await fetch(`${BACKEND_URL}/api/budget/record-usage`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ duration_seconds: durationSeconds, estimated_cost: estimatedCost }),
  });

  if (!response.ok) {
    throw new Error(`Failed to record session usage: HTTP ${response.status}`);
  }

  return response.json();
}

export async function resetDailyBudget(): Promise<{ reset: boolean; date: string }> {
  const response = await fetch(`${BACKEND_URL}/api/budget/reset`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to reset budget: HTTP ${response.status}`);
  }

  return response.json();
}

export async function fetchSettings(): Promise<AppSettings> {
  const response = await fetch(`${BACKEND_URL}/api/settings`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch settings: HTTP ${response.status}`);
  }

  return response.json();
}

export async function updateSettings(payload: UpdateSettingsPayload): Promise<AppSettings> {
  const response = await fetch(`${BACKEND_URL}/api/settings`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to update settings: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

// ── Applications (Personal App Access Manager) ──────────────────────

export interface ManagedApp {
  id: string;
  name: string;
  target_path: string;
  target_type: 'executable' | 'packaged';
  category: string;
  icon_path: string | null;
  is_enabled: boolean;
  is_available: boolean;
  last_launched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AppListResponse {
  applications: ManagedApp[];
  total_count: number;
  enabled_count: number;
  disabled_count: number;
  categories: string[];
}

export interface AppLaunchResponse {
  launched: boolean;
  app_id: string;
  name: string;
  mode?: string;
  message: string;
}

export async function fetchApplications(filters?: {
  search?: string;
  category?: string;
  enabled_only?: boolean;
}): Promise<AppListResponse> {
  const params = new URLSearchParams();
  if (filters?.search) params.append('search', filters.search);
  if (filters?.category && filters.category !== 'All') params.append('category', filters.category);
  if (filters?.enabled_only) params.append('enabled_only', 'true');

  const query = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${BACKEND_URL}/api/apps${query}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to fetch applications: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

export async function refreshApplications(): Promise<AppListResponse> {
  const response = await fetch(`${BACKEND_URL}/api/apps/refresh`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to refresh applications: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

export async function updateAppPermission(appId: string, isEnabled: boolean): Promise<ManagedApp> {
  const response = await fetch(`${BACKEND_URL}/api/apps/${encodeURIComponent(appId)}/permission`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ is_enabled: isEnabled }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to update permission: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

export async function launchApplication(appId: string): Promise<AppLaunchResponse> {
  const response = await fetch(`${BACKEND_URL}/api/apps/${encodeURIComponent(appId)}/launch`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Failed to launch application: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}

// ── Universal Automation Commands ───────────────────────────────────

export interface OperationStepResult {
  step_id: string;
  action_type: string;
  status: 'planned' | 'awaiting_approval' | 'running' | 'verifying' | 'completed' | 'failed' | 'cancelled';
  message: string;
  evidence?: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
  error_code?: string;
}

export interface OperationExecutionResult {
  operation_id: string;
  intent: string;
  target_app_id?: string | null;
  target_app_name?: string | null;
  status: 'planned' | 'awaiting_approval' | 'running' | 'verifying' | 'completed' | 'failed' | 'cancelled';
  steps_planned: number;
  steps_completed: number;
  step_results: OperationStepResult[];
  verification_evidence?: Record<string, unknown>;
  error_message?: string | null;
  message?: string | null;
  requires_approval?: boolean;
  approval_id?: string | null;
}

export async function executeCommand(command: string): Promise<OperationExecutionResult> {
  const response = await fetch(`${BACKEND_URL}/api/commands/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ command }),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Command failed: HTTP ${response.status}`;
    throw new Error(msg);
  }

  return response.json();
}
