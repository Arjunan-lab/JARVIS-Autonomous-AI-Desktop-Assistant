import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApplicationsPanel } from './ApplicationsPanel';
import * as api from '../lib/api';

vi.mock('../lib/api', () => ({
  fetchApplications: vi.fn(),
  refreshApplications: vi.fn(),
  updateAppPermission: vi.fn(),
  launchApplication: vi.fn(),
}));

describe('ApplicationsPanel Component', () => {
  const mockApps: api.ManagedApp[] = [
    {
      id: 'app-chrome-001',
      name: 'Google Chrome',
      target_path: 'C:\\Program Files\\Google\\Chrome\\chrome.exe',
      target_type: 'executable',
      category: 'Browsers',
      icon_path: null,
      is_enabled: true,
      is_available: true,
      last_launched_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'app-calc-002',
      name: 'Calculator',
      target_path: 'C:\\Windows\\System32\\calc.exe',
      target_type: 'executable',
      category: 'Productivity',
      icon_path: null,
      is_enabled: false, // Default deny
      is_available: true,
      last_launched_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'app-code-003',
      name: 'Visual Studio Code',
      target_path: 'C:\\Users\\User\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe',
      target_type: 'executable',
      category: 'Development',
      icon_path: null,
      is_enabled: false,
      is_available: false, // Missing on disk
      last_launched_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  const mockListResponse: api.AppListResponse = {
    applications: mockApps,
    total_count: 3,
    enabled_count: 1,
    disabled_count: 2,
    categories: ['Browsers', 'Development', 'Productivity'],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchApplications).mockResolvedValue(mockListResponse);
    vi.mocked(api.refreshApplications).mockResolvedValue(mockListResponse);
    vi.mocked(api.updateAppPermission).mockImplementation(async (id, isEnabled) => {
      const found = mockApps.find((a) => a.id === id);
      return {
        ...(found || mockApps[0]),
        id,
        is_enabled: isEnabled,
      };
    });
    vi.mocked(api.launchApplication).mockResolvedValue({
      launched: true,
      app_id: 'app-chrome-001',
      name: 'Google Chrome',
      mode: 'simulated',
      message: 'Application launched successfully',
    });
  });

  it('renders panel header, summary metrics, and application cards', async () => {
    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Personal App Access Manager')).toBeInTheDocument();
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
      expect(screen.getByText('Calculator')).toBeInTheDocument();
      expect(screen.getByText('Visual Studio Code')).toBeInTheDocument();
    });

    expect(screen.getByText('Total Discovered')).toBeInTheDocument();
    expect(screen.getByText('Authorized (Enabled)')).toBeInTheDocument();
    expect(screen.getByText('Blocked (Default Deny)')).toBeInTheDocument();
  });

  it('filters applications when searching', async () => {
    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search applications by name or path…');
    fireEvent.change(searchInput, { target: { value: 'chrome' } });

    await waitFor(() => {
      expect(api.fetchApplications).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'chrome' })
      );
    });
  });

  it('filters applications by category pill', async () => {
    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByRole('radio', { name: 'Browsers' })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('radio', { name: 'Browsers' }));

    await waitFor(() => {
      expect(api.fetchApplications).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'Browsers' })
      );
    });
  });

  it('toggles application permission and updates status', async () => {
    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Calculator')).toBeInTheDocument();
    });

    const calcCard = screen.getByTestId('app-card-app-calc-002');
    const toggleBtn = calcCard.querySelector('button[role="switch"]');
    expect(toggleBtn).toBeInTheDocument();

    fireEvent.click(toggleBtn!);

    await waitFor(() => {
      expect(api.updateAppPermission).toHaveBeenCalledWith('app-calc-002', true);
    });
  });

  it('launches enabled application and disables launch for disabled application', async () => {
    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
    });

    // Chrome is enabled -> launch button should be enabled
    const chromeCard = screen.getByTestId('app-card-app-chrome-001');
    const launchBtn = chromeCard.querySelector('.app-launch-btn') as HTMLButtonElement;
    expect(launchBtn).not.toBeDisabled();

    fireEvent.click(launchBtn);

    await waitFor(() => {
      expect(api.launchApplication).toHaveBeenCalledWith('app-chrome-001');
    });

    // Calculator is disabled -> launch button must be disabled
    const calcCard = screen.getByTestId('app-card-app-calc-002');
    const calcLaunchBtn = calcCard.querySelector('.app-launch-btn') as HTMLButtonElement;
    expect(calcLaunchBtn).toBeDisabled();

    // Code is unavailable on disk -> launch button must be disabled
    const codeCard = screen.getByTestId('app-card-app-code-003');
    const codeLaunchBtn = codeCard.querySelector('.app-launch-btn') as HTMLButtonElement;
    expect(codeLaunchBtn).toBeDisabled();
  });

  it('refreshes application discovery when Refresh Discovery is clicked', async () => {
    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Google Chrome')).toBeInTheDocument();
    });

    const refreshBtn = screen.getByRole('button', { name: /Refresh Application Discovery/i });
    expect(refreshBtn).not.toBeDisabled();
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(api.refreshApplications).toHaveBeenCalled();
    });
  });

  it('renders empty state when no applications are returned', async () => {
    vi.mocked(api.fetchApplications).mockResolvedValueOnce({
      applications: [],
      total_count: 0,
      enabled_count: 0,
      disabled_count: 0,
      categories: [],
    });

    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('No Applications Found')).toBeInTheDocument();
    });
  });

  it('renders error state when fetching fails', async () => {
    vi.mocked(api.fetchApplications).mockRejectedValueOnce(new Error('Network connection refused'));

    render(<ApplicationsPanel />);

    await waitFor(() => {
      expect(screen.getByText('Application Registry Error')).toBeInTheDocument();
      expect(screen.getByText('Network connection refused')).toBeInTheDocument();
    });
  });
});
