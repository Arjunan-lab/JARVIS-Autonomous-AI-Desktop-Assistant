import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskPanel } from './TaskPanel';
import * as api from '../lib/api';

vi.mock('../lib/api', () => ({
  fetchTasks: vi.fn(),
  fetchDueReminders: vi.fn(),
  createTask: vi.fn(),
  updateTask: vi.fn(),
  deleteTask: vi.fn(),
}));

describe('TaskPanel Component', () => {
  const mockTasks: api.Task[] = [
    {
      id: 'task-1',
      title: 'Review flight telemetry',
      description: 'Check navigation logs',
      due_date: new Date(Date.now() + 86400000).toISOString(),
      status: 'pending',
      priority: 'high',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'task-2',
      title: 'Calibrate audio sensors',
      description: null,
      due_date: null,
      status: 'completed',
      priority: 'low',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchTasks).mockResolvedValue({
      tasks: mockTasks,
      total: 2,
      pending_count: 1,
      completed_count: 1,
    });
    vi.mocked(api.fetchDueReminders).mockResolvedValue([]);
  });

  it('renders task list with headings and priority chips', async () => {
    render(<TaskPanel />);

    await waitFor(() => {
      expect(screen.getByText('Review flight telemetry')).toBeInTheDocument();
      expect(screen.getByText('Calibrate audio sensors')).toBeInTheDocument();
      expect(screen.getAllByText('high').length).toBeGreaterThan(0);
    });
  });

  it('displays reminders banner when tasks are due', async () => {
    vi.mocked(api.fetchDueReminders).mockResolvedValueOnce([mockTasks[0]]);

    render(<TaskPanel />);

    await waitFor(() => {
      expect(screen.getByText(/require attention:/i)).toBeInTheDocument();
    });
  });

  it('creates a new task via form submission', async () => {
    const newTask: api.Task = {
      id: 'task-3',
      title: 'Inspect core power cells',
      description: 'Check voltage levels',
      due_date: null,
      status: 'pending',
      priority: 'medium',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    vi.mocked(api.createTask).mockResolvedValueOnce(newTask);

    render(<TaskPanel />);

    const newBtn = screen.getByRole('button', { name: /New Task/i });
    fireEvent.click(newBtn);

    const input = screen.getByPlaceholderText(/Task title/i);
    fireEvent.change(input, { target: { value: 'Inspect core power cells' } });

    const saveBtn = screen.getByRole('button', { name: /Save Task/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.createTask).toHaveBeenCalledWith(
        expect.objectContaining({ title: 'Inspect core power cells' })
      );
    });
  });

  it('toggles task completion status', async () => {
    vi.mocked(api.updateTask).mockResolvedValueOnce({
      ...mockTasks[0],
      status: 'completed',
    });

    render(<TaskPanel />);

    await waitFor(() => {
      expect(screen.getByText('Review flight telemetry')).toBeInTheDocument();
    });

    const checkbox = screen.getByRole('button', { name: /Mark as completed/i });
    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(api.updateTask).toHaveBeenCalledWith('task-1', { status: 'completed' });
    });
  });

  it('deletes a task when trash button is clicked', async () => {
    vi.mocked(api.deleteTask).mockResolvedValueOnce();

    render(<TaskPanel />);

    await waitFor(() => {
      expect(screen.getByText('Review flight telemetry')).toBeInTheDocument();
    });

    const deleteBtns = screen.getAllByRole('button', { name: /Delete task/i });
    fireEvent.click(deleteBtns[0]);

    await waitFor(() => {
      expect(api.deleteTask).toHaveBeenCalledWith('task-1');
    });
  });
});
