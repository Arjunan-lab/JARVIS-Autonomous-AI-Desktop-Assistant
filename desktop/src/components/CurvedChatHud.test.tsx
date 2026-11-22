import '@testing-library/jest-dom/vitest';
import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CurvedChatHud, type ChatHudMessage } from './CurvedChatHud';

describe('CurvedChatHud Component', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders nothing when message is null', () => {
    const { container } = render(<CurvedChatHud message={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders curved HUD with typewriter animation and sender tag', () => {
    const msg: ChatHudMessage = {
      id: 'test-1',
      sender: 'assistant',
      text: 'Good day, sir. Systems are nominal.',
    };

    render(<CurvedChatHud message={msg} vanishDelayMs={5000} />);

    expect(screen.getByText(/JARVIS · NEURAL SYNTHESIS/i)).toBeInTheDocument();
    expect(screen.getByText(/HUD \/\/ ACTIVE/i)).toBeInTheDocument();

    // Advance typewriter timer (18ms * length)
    act(() => {
      vi.advanceTimersByTime(18 * msg.text.length + 50);
    });

    expect(screen.getByText('Good day, sir. Systems are nominal.')).toBeInTheDocument();
  });

  it('vanishes and calls onVanish after 5 seconds timegap', () => {
    const onVanishMock = vi.fn();
    const msg: ChatHudMessage = {
      id: 'test-2',
      sender: 'user',
      text: 'What is the system status?',
    };

    render(<CurvedChatHud message={msg} onVanish={onVanishMock} vanishDelayMs={5000} />);

    // Fast-forward typewriter effect
    act(() => {
      vi.advanceTimersByTime(18 * msg.text.length + 50);
    });

    expect(onVanishMock).not.toHaveBeenCalled();

    // Advance 5000ms vanish timegap + 800ms fade transition
    act(() => {
      vi.advanceTimersByTime(5800);
    });

    expect(onVanishMock).toHaveBeenCalledTimes(1);
  });
});
