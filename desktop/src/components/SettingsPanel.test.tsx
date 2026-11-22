import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { SettingsPanel } from './SettingsPanel';
import * as api from '../lib/api';

vi.mock('../lib/api', () => ({
  fetchBudgetStatus: vi.fn(),
  fetchSettings: vi.fn(),
  resetDailyBudget: vi.fn(),
  updateSettings: vi.fn(),
}));

describe('SettingsPanel Component', () => {
  const mockBudget: api.BudgetStatus = {
    date: '2026-10-16',
    limit_usd: 1.0,
    spent_usd: 0.25,
    remaining_usd: 0.75,
    is_budget_exceeded: false,
    sessions_today: 3,
    duration_seconds_today: 180,
    active_sessions: 0,
  };

  const mockSettings: api.AppSettings = {
    app_name: 'JARVIS',
    app_env: 'test',
    openai_model: 'gpt-realtime-mini',
    openai_voice: 'marin',
    has_api_key: true,
    allowed_dirs: ['F:/Coding/docs'],
    max_daily_budget_usd: 1.0,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchBudgetStatus).mockResolvedValue(mockBudget);
    vi.mocked(api.fetchSettings).mockResolvedValue(mockSettings);
  });

  it('renders budget metrics, voice configuration, and allowed sandboxes', async () => {
    render(<SettingsPanel />);

    await waitFor(() => {
      expect(
        screen.getByText('System Settings & Budget Safeguards')
      ).toBeInTheDocument();
      expect(screen.getByText('$0.25 / $1.00 USD')).toBeInTheDocument();
      expect(screen.getByText('Remaining: $0.75')).toBeInTheDocument();
      expect(screen.getByText('gpt-realtime-mini')).toBeInTheDocument();
      expect(screen.getByText('marin')).toBeInTheDocument();
      expect(screen.getByText('F:/Coding/docs')).toBeInTheDocument();
    });
  });

  it('updates daily budget limit via the form', async () => {
    vi.mocked(api.updateSettings).mockResolvedValueOnce({
      ...mockSettings,
      max_daily_budget_usd: 2.5,
    });

    render(<SettingsPanel />);

    await waitFor(() => {
      expect(screen.getByText('$0.25 / $1.00 USD')).toBeInTheDocument();
    });

    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '2.50' } });

    const updateBtn = screen.getByRole('button', { name: /Update Limit/i });
    fireEvent.click(updateBtn);

    await waitFor(() => {
      expect(api.updateSettings).toHaveBeenCalledWith({
        max_daily_budget_usd: 2.5,
      });
      expect(
        screen.getByText(/Daily API budget limit updated to \$2\.50 USD/i)
      ).toBeInTheDocument();
    });
  });

  it('resets the daily budget counter when reset is clicked', async () => {
    vi.mocked(api.resetDailyBudget).mockResolvedValueOnce({
      reset: true,
      date: '2026-10-16',
    });

    render(<SettingsPanel />);

    await waitFor(() => {
      expect(screen.getByText('$0.25 / $1.00 USD')).toBeInTheDocument();
    });

    const resetBtn = screen.getByRole('button', { name: /Reset/i });
    fireEvent.click(resetBtn);

    await waitFor(() => {
      expect(api.resetDailyBudget).toHaveBeenCalled();
      expect(
        screen.getByText(/Daily API spend counter has been reset to \$0\.00/i)
      ).toBeInTheDocument();
    });
  });
});
