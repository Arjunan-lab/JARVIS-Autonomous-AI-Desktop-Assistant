import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryPanel } from './MemoryPanel';
import * as api from '../lib/api';

vi.mock('../lib/api', () => ({
  fetchMemories: vi.fn(),
  createMemory: vi.fn(),
  updateMemory: vi.fn(),
  deleteMemory: vi.fn(),
  searchMemoryAndDocs: vi.fn(),
}));

describe('MemoryPanel Component', () => {
  const mockMemories: api.Memory[] = [
    {
      id: 'mem-1',
      category: 'preference',
      content: 'Always respond in concise technical terms',
      approved: true,
      source: 'user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'mem-2',
      category: 'project',
      content: 'JARVIS architecture uses WebRTC and SQLite',
      approved: true,
      source: 'user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'mem-3',
      category: 'knowledge',
      content: 'Unapproved experimental notes',
      approved: false,
      source: 'assistant',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchMemories).mockResolvedValue({
      memories: mockMemories,
      total: 3,
      preference_count: 1,
      project_count: 1,
      knowledge_count: 1,
      task_history_count: 0,
    });
  });

  it('renders memory list with headings, category chips, and content', async () => {
    render(<MemoryPanel />);

    await waitFor(() => {
      expect(screen.getByText('Memory & Knowledge Base')).toBeInTheDocument();
      expect(
        screen.getByText('Always respond in concise technical terms')
      ).toBeInTheDocument();
      expect(
        screen.getByText('JARVIS architecture uses WebRTC and SQLite')
      ).toBeInTheDocument();
      expect(screen.getByText('Preferences')).toBeInTheDocument();
    });
  });

  it('filters by category when category chip is clicked', async () => {
    render(<MemoryPanel />);

    await waitFor(() => {
      expect(
        screen.getByText('Always respond in concise technical terms')
      ).toBeInTheDocument();
    });

    const prefChip = screen.getByRole('button', { name: /Preferences/i });
    fireEvent.click(prefChip);

    await waitFor(() => {
      expect(api.fetchMemories).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'preference' })
      );
    });
  });

  it('creates a new memory via modal submission', async () => {
    const newMem: api.Memory = {
      id: 'mem-4',
      category: 'preference',
      content: 'Coffee temperature 65C',
      approved: true,
      source: 'user',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    vi.mocked(api.createMemory).mockResolvedValueOnce(newMem);

    render(<MemoryPanel />);

    const newBtn = screen.getByRole('button', { name: /New Memory/i });
    fireEvent.click(newBtn);

    const textarea = screen.getByPlaceholderText(/Enter memory details/i);
    fireEvent.change(textarea, { target: { value: 'Coffee temperature 65C' } });

    const saveBtn = screen.getByRole('button', { name: /Save Memory/i });
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.createMemory).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'Coffee temperature 65C',
          category: 'preference',
          approved: true,
        })
      );
    });
  });

  it('toggles approval status when approval badge is clicked', async () => {
    vi.mocked(api.updateMemory).mockResolvedValueOnce({
      ...mockMemories[0],
      approved: false,
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(
        screen.getByText('Always respond in concise technical terms')
      ).toBeInTheDocument();
    });

    const approvalBtns = screen.getAllByTitle(/toggle approved memory status/i);
    fireEvent.click(approvalBtns[0]);

    await waitFor(() => {
      expect(api.updateMemory).toHaveBeenCalledWith('mem-1', {
        approved: false,
      });
    });
  });

  it('edits memory content inline and saves', async () => {
    vi.mocked(api.updateMemory).mockResolvedValueOnce({
      ...mockMemories[0],
      content: 'Always respond with high precision technical terms',
    });

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(
        screen.getByText('Always respond in concise technical terms')
      ).toBeInTheDocument();
    });

    const editBtns = screen.getAllByTitle('Edit memory');
    fireEvent.click(editBtns[0]);

    const textarea = screen.getByDisplayValue(
      'Always respond in concise technical terms'
    );
    fireEvent.change(textarea, {
      target: { value: 'Always respond with high precision technical terms' },
    });

    const saveBtn = screen.getByTitle('Save changes');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(api.updateMemory).toHaveBeenCalledWith(
        'mem-1',
        expect.objectContaining({
          content: 'Always respond with high precision technical terms',
        })
      );
    });
  });

  it('deletes a memory when trash icon is clicked', async () => {
    vi.mocked(api.deleteMemory).mockResolvedValueOnce();

    render(<MemoryPanel />);

    await waitFor(() => {
      expect(
        screen.getByText('Always respond in concise technical terms')
      ).toBeInTheDocument();
    });

    const deleteBtns = screen.getAllByTitle('Delete memory');
    fireEvent.click(deleteBtns[0]);

    await waitFor(() => {
      expect(api.deleteMemory).toHaveBeenCalledWith('mem-1');
    });
  });

  it('searches memories and renders matched local documents', async () => {
    vi.mocked(api.searchMemoryAndDocs).mockResolvedValueOnce({
      query: 'telemetry',
      memories: [mockMemories[1]],
      documents: [
        {
          file_path: 'F:/Coding/docs/flight_manual.md',
          file_name: 'flight_manual.md',
          snippet: 'Telemetry calibrated to standard orbit',
          line_number: 42,
        },
      ],
    });

    render(<MemoryPanel />);

    const searchInput = screen.getByPlaceholderText(/Search memories or documents/i);
    fireEvent.change(searchInput, { target: { value: 'telemetry' } });

    await waitFor(() => {
      expect(api.searchMemoryAndDocs).toHaveBeenCalledWith('telemetry', undefined, true);
      expect(screen.getByText(/Matched Local Documents/i)).toBeInTheDocument();
      expect(screen.getByText('flight_manual.md')).toBeInTheDocument();
      expect(screen.getByText('Line 42')).toBeInTheDocument();
    });
  });
});
