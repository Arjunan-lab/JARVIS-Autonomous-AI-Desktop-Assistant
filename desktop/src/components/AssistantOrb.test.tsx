import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AssistantOrb, type OrbState } from './AssistantOrb';

describe('AssistantOrb Component', () => {
  const states: OrbState[] = ['idle', 'listening', 'thinking', 'speaking', 'error', 'disconnected'];

  states.forEach((state) => {
    it(`renders correctly in ${state} state`, () => {
      render(<AssistantOrb state={state} />);
      const orb = screen.getByRole('button');
      expect(orb).toHaveClass(`state-${state}`);
      expect(orb).toHaveAttribute('aria-label', `JARVIS Core State: ${state}`);
    });
  });

  it('renders audio reactive scaling', () => {
    const { container } = render(<AssistantOrb state="listening" audioLevel={0.8} />);
    const outerWave = container.querySelector('.orb-wave-outer');
    expect(outerWave).toBeInTheDocument();
  });
});
