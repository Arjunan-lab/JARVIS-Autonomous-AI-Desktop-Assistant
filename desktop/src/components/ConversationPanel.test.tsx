import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ConversationPanel, type Message } from './ConversationPanel';

describe('ConversationPanel Component', () => {
  const sampleMessages: Message[] = [
    {
      id: '1',
      sender: 'user',
      text: 'Good morning JARVIS',
      timestamp: '10:00 AM',
    },
    {
      id: '2',
      sender: 'assistant',
      text: 'Good morning. Systems operating at peak efficiency.',
      timestamp: '10:01 AM',
      toolCalls: [{ name: 'check_status', status: 'success' }],
    },
  ];

  it('renders messages and tool badges', () => {
    render(<ConversationPanel messages={sampleMessages} onSendMessage={vi.fn()} />);

    expect(screen.getByText('Good morning JARVIS')).toBeInTheDocument();
    expect(screen.getByText(/Systems operating at peak efficiency/i)).toBeInTheDocument();
    expect(screen.getByText('check_status')).toBeInTheDocument();
  });

  it('submits typed message on enter or button click', () => {
    const handleSend = vi.fn();
    render(<ConversationPanel messages={[]} onSendMessage={handleSend} />);

    const textarea = screen.getByLabelText(/Type message to JARVIS/i);
    fireEvent.change(textarea, { target: { value: 'Schedule a meeting' } });

    const sendBtn = screen.getByRole('button', { name: /Send message/i });
    fireEvent.click(sendBtn);

    expect(handleSend).toHaveBeenCalledWith('Schedule a meeting');
  });

  it('renders quick prompt buttons on empty state', () => {
    const handleSend = vi.fn();
    render(<ConversationPanel messages={[]} onSendMessage={handleSend} />);

    const chip = screen.getByText(/Check system health/i);
    fireEvent.click(chip);

    expect(handleSend).toHaveBeenCalledWith(expect.stringContaining('health'));
  });
});
