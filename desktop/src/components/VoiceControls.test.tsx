import '@testing-library/jest-dom/vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { VoiceControls } from './VoiceControls';

describe('VoiceControls Component', () => {
  it('calls onToggleVoice when mic button is clicked', () => {
    const handleToggleVoice = vi.fn();
    render(
      <VoiceControls
        isVoiceActive={false}
        isMuted={false}
        hasMicPermission={true}
        onToggleVoice={handleToggleVoice}
        onToggleMute={vi.fn()}
        onDisconnect={vi.fn()}
      />
    );

    const micBtn = screen.getByRole('button', { name: /Start Voice Mode/i });
    fireEvent.click(micBtn);
    expect(handleToggleVoice).toHaveBeenCalledTimes(1);
  });

  it('calls onToggleMute and onDisconnect', () => {
    const handleToggleMute = vi.fn();
    const handleDisconnect = vi.fn();

    render(
      <VoiceControls
        isVoiceActive={true}
        isMuted={false}
        hasMicPermission={true}
        onToggleVoice={vi.fn()}
        onToggleMute={handleToggleMute}
        onDisconnect={handleDisconnect}
      />
    );

    const muteBtn = screen.getByRole('button', { name: /Mute Audio/i });
    fireEvent.click(muteBtn);
    expect(handleToggleMute).toHaveBeenCalledTimes(1);

    const stopBtn = screen.getByRole('button', { name: /Emergency Stop/i });
    fireEvent.click(stopBtn);
    expect(handleDisconnect).toHaveBeenCalledTimes(1);
  });

  it('shows permission warning when access is denied', () => {
    render(
      <VoiceControls
        isVoiceActive={false}
        isMuted={false}
        hasMicPermission={false}
        onToggleVoice={vi.fn()}
        onToggleMute={vi.fn()}
        onDisconnect={vi.fn()}
      />
    );

    expect(screen.getByText(/Microphone access was denied/i)).toBeInTheDocument();
  });
});
