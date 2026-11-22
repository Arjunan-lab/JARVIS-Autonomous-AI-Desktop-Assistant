import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApprovalDialog } from './ApprovalDialog';
import * as api from '../lib/api';

vi.mock('../lib/api', () => ({
  fetchApprovals: vi.fn(),
  approveAction: vi.fn(),
  rejectAction: vi.fn(),
  requestAction: vi.fn(),
  fetchAuditEvents: vi.fn(),
}));

describe('ApprovalDialog Component', () => {
  const mockApprovals: api.Approval[] = [
    {
      id: 'appr-1',
      action_type: 'delete_file',
      arguments: { file_path: 'F:/Coding/docs/cache.txt' },
      policy: 'explicit_confirmation',
      status: 'pending',
      expires_at: new Date(Date.now() + 300000).toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  const mockAuditEvents: api.AuditEvent[] = [
    {
      id: 'aud-1',
      action_id: 'appr-1',
      action_type: 'delete_file',
      outcome: 'success',
      details: { file_path: 'F:/Coding/docs/cache.txt' },
      timestamp: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchApprovals).mockResolvedValue({
      approvals: mockApprovals,
      total: 1,
      pending_count: 1,
    });
    vi.mocked(api.fetchAuditEvents).mockResolvedValue({
      events: mockAuditEvents,
      total: 1,
    });
  });

  it('renders pending approval cards with action type and parameters', async () => {
    render(<ApprovalDialog />);

    await waitFor(() => {
      expect(screen.getByText('Security Approvals & Audit Trail')).toBeInTheDocument();
      expect(screen.getByText('delete_file')).toBeInTheDocument();
      expect(screen.getAllByText(/cache\.txt/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByRole('button', { name: /Authorize & Execute/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Reject Action/i })).toBeInTheDocument();
    });
  });

  it('renders nominal status when no approvals are pending', async () => {
    vi.mocked(api.fetchApprovals).mockResolvedValueOnce({
      approvals: [],
      total: 0,
      pending_count: 0,
    });

    render(<ApprovalDialog />);

    await waitFor(() => {
      expect(screen.getByText(/All Systems Nominal/i)).toBeInTheDocument();
      expect(screen.getByText(/Zero pending actions awaiting authorization/i)).toBeInTheDocument();
    });
  });

  it('approves an action when Authorize & Execute is clicked', async () => {
    vi.mocked(api.approveAction).mockResolvedValueOnce({
      approval_id: 'appr-1',
      status: 'executed',
    });

    render(<ApprovalDialog />);

    await waitFor(() => {
      expect(screen.getByText('delete_file')).toBeInTheDocument();
    });

    const approveBtn = screen.getByRole('button', { name: /Authorize & Execute/i });
    fireEvent.click(approveBtn);

    // Verify detailed final confirmation modal displays action explanation
    expect(screen.getByText('FINAL ACTION CONFIRMATION')).toBeInTheDocument();
    expect(screen.getAllByText(/Permanently delete file/i).length).toBeGreaterThanOrEqual(1);

    const confirmBtn = screen.getByRole('button', { name: /Confirm & Execute Now/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(api.approveAction).toHaveBeenCalledWith('appr-1');
      expect(screen.getByText(/successfully authorized and executed/i)).toBeInTheDocument();
    });
  });

  it('rejects an action when Reject Action is clicked', async () => {
    vi.mocked(api.rejectAction).mockResolvedValueOnce({
      approval_id: 'appr-1',
      status: 'rejected',
    });

    render(<ApprovalDialog />);

    await waitFor(() => {
      expect(screen.getByText('delete_file')).toBeInTheDocument();
    });

    const rejectBtn = screen.getByRole('button', { name: /Reject Action/i });
    fireEvent.click(rejectBtn);

    await waitFor(() => {
      expect(api.rejectAction).toHaveBeenCalledWith('appr-1');
      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
    });
  });

  it('switches to Audit History view and renders logged events', async () => {
    render(<ApprovalDialog />);

    const auditTab = screen.getByRole('button', { name: /Audit History Trail/i });
    fireEvent.click(auditTab);

    await waitFor(() => {
      expect(api.fetchAuditEvents).toHaveBeenCalled();
      expect(screen.getByText('success')).toBeInTheDocument();
    });
  });
});
