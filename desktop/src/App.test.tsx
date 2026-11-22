import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App, { resetStarterVoiceoverSession } from './App';
import * as api from './lib/api';

vi.mock('./lib/api', () => ({
  fetchHealth: vi.fn(),
  fetchTasks: vi.fn(),
  fetchDueReminders: vi.fn(),
  fetchMemories: vi.fn(),
  fetchApprovals: vi.fn(),
  fetchBudgetStatus: vi.fn(),
  fetchSettings: vi.fn(),
  fetchApplications: vi.fn().mockResolvedValue({
    applications: [],
    total_count: 0,
    enabled_count: 0,
    disabled_count: 0,
    categories: [],
  }),
  refreshApplications: vi.fn().mockResolvedValue({
    applications: [],
    total_count: 0,
    enabled_count: 0,
    disabled_count: 0,
    categories: [],
  }),
  updateAppPermission: vi.fn(),
  launchApplication: vi.fn(),
  executeCommand: vi.fn().mockResolvedValue({
    operation_id: 'op-test-1',
    intent: 'test intent',
    target_app_id: 'notepad_app_id',
    target_app_name: 'Notepad',
    status: 'completed',
    steps_planned: 1,
    steps_completed: 1,
    step_results: [
      {
        step_id: 'step-0',
        action_type: 'type_text',
        status: 'completed',
        message: 'Typed text successfully',
        evidence: {},
      },
    ],
    verification_evidence: { verified: true, message: 'Text verified' },
    error_message: null,
  }),
  recordSessionUsage: vi.fn().mockResolvedValue({ duration_seconds: 0, added_cost_usd: 0, total_spent_today: 0 }),
}));

describe('App Desktop Shell & Cockpit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetStarterVoiceoverSession();
    // Mock scrollIntoView for jsdom
    window.HTMLElement.prototype.scrollIntoView = vi.fn();
  });

  it('renders JARVIS title and assistant cockpit by default', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });

    render(<App />);

    expect(screen.getAllByText('JARVIS').length).toBeGreaterThan(0);
    expect(screen.getByText('Assistant Cockpit')).toBeInTheDocument();
    expect(screen.getByText(/Conversation Log/i)).toBeInTheDocument();
    expect(screen.getByText(/Hello boss.*hope you are doing well/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });
  });

  it('switches to Tasks & Reminders view', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });
    vi.mocked(api.fetchTasks).mockResolvedValueOnce({
      tasks: [],
      total: 0,
      pending_count: 0,
      completed_count: 0,
    });
    vi.mocked(api.fetchDueReminders).mockResolvedValueOnce([]);

    render(<App />);

    const tasksTab = screen.getByRole('button', { name: /Tasks & Reminders/i });
    fireEvent.click(tasksTab);

    await waitFor(() => {
      expect(screen.getByText(/Task & Reminder Manager/i)).toBeInTheDocument();
    });
  });

  it('switches to Architecture & Data view', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });

    const archTab = screen.getByRole('button', { name: /Architecture & Data/i });
    fireEvent.click(archTab);

    expect(screen.getByText(/SYSTEM ARCHITECTURE/i)).toBeInTheDocument();
    expect(screen.getByText(/SQLite Persistence/i)).toBeInTheDocument();
  });

  it('switches to Memory & Knowledge view', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });
    vi.mocked(api.fetchMemories).mockResolvedValueOnce({
      memories: [],
      total: 0,
      preference_count: 0,
      project_count: 0,
      knowledge_count: 0,
      task_history_count: 0,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });

    const memoryTab = screen.getByRole('button', { name: /Memory & Knowledge/i });
    fireEvent.click(memoryTab);

    await waitFor(() => {
      expect(screen.getByText(/Memory & Knowledge Base/i)).toBeInTheDocument();
    });
  });

  it('switches to Approvals & Audit view', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });
    vi.mocked(api.fetchApprovals).mockResolvedValue({
      approvals: [],
      total: 0,
      pending_count: 0,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });

    const approvalsTab = screen.getByRole('button', { name: /Approvals & Audit/i });
    fireEvent.click(approvalsTab);

    await waitFor(() => {
      expect(screen.getByText(/Security Approvals & Audit Trail/i)).toBeInTheDocument();
    });
  });

  it('switches to Settings & Budget view', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });
    vi.mocked(api.fetchBudgetStatus).mockResolvedValue({
      date: '2026-10-16',
      limit_usd: 5.0,
      spent_usd: 0.12,
      remaining_usd: 4.88,
      is_budget_exceeded: false,
      sessions_today: 1,
      duration_seconds_today: 45,
      active_sessions: 0,
    });
    vi.mocked(api.fetchSettings).mockResolvedValue({
      app_name: 'JARVIS',
      app_env: 'test',
      openai_model: 'gpt-realtime-mini',
      openai_voice: 'marin',
      has_api_key: true,
      allowed_dirs: ['C:\\Users\\Test\\Documents'],
      max_daily_budget_usd: 5.0,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });

    const settingsTab = screen.getByRole('button', { name: /Settings & Budget/i });
    fireEvent.click(settingsTab);

    await waitFor(() => {
      expect(screen.getByText(/System Settings & Budget Safeguards/i)).toBeInTheDocument();
    });
  });

  it('switches to App Permissions view', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Online/i)).toBeInTheDocument();
    });

    const appsTab = screen.getByRole('button', { name: /App Permissions/i });
    fireEvent.click(appsTab);

    await waitFor(() => {
      expect(screen.getByText(/Personal App Access Manager/i)).toBeInTheDocument();
    });
  });

  it('handles backend offline status gracefully', async () => {
    vi.mocked(api.fetchHealth).mockRejectedValueOnce(new Error('Network error'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Offline/i)).toBeInTheDocument();
    });
  });

  it('executes user automation command via executeCommand API', async () => {
    vi.mocked(api.fetchHealth).mockResolvedValueOnce({
      status: 'ok',
      service: 'jarvis',
      version: '0.1.0',
    });

    render(<App />);

    const inputs = screen.getAllByLabelText(/Type message to JARVIS/i);
    const input = inputs[0];
    fireEvent.change(input, { target: { value: 'open Notepad and write Hello' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.executeCommand).toHaveBeenCalledWith('open Notepad and write Hello');
    });
  });
});
