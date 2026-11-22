import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ensureVoicesLoaded,
  sanitizeTextForSpeech,
  speakJarvis,
  stopJarvisSpeech,
  unlockSpeechSynthesis,
} from './speech';

class MockSpeechSynthesisUtterance {
  text: string;
  rate = 1;
  pitch = 1;
  voice: SpeechSynthesisVoice | null = null;
  onstart: ((e: Event) => void) | null = null;
  onend: ((e: Event) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;

  constructor(text = '') {
    this.text = text;
  }
}

describe('Speech Library', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('SpeechSynthesisUtterance', MockSpeechSynthesisUtterance);
  });

  afterEach(() => {
    stopJarvisSpeech();
  });

  it('sanitizes text properly for spoken dialogue', () => {
    const raw = '```js\nconsole.log("test");\n``` Check `code` and [link](http://example.com) with *bold* text.';
    const clean = sanitizeTextForSpeech(raw);
    expect(clean).toContain('Code block omitted.');
    expect(clean).toContain('Check code and link with bold text.');
    expect(clean).not.toContain('```');
    expect(clean).not.toContain('*');
  });

  it('ensures voices can be resolved when voices are available', async () => {
    const mockVoice = { name: 'Microsoft Daniel - English (United Kingdom)', lang: 'en-GB' } as SpeechSynthesisVoice;
    vi.stubGlobal('speechSynthesis', {
      getVoices: vi.fn().mockReturnValue([mockVoice]),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      speak: vi.fn(),
      cancel: vi.fn(),
      resume: vi.fn(),
    });

    const voices = await ensureVoicesLoaded();
    expect(voices.length).toBe(1);
    expect(voices[0].name).toContain('Daniel');
  });

  it('speaks text via speakJarvis and triggers lifecycle callbacks', async () => {
    const mockVoice = { name: 'Microsoft George - English (United Kingdom)', lang: 'en-GB' } as SpeechSynthesisVoice;
    let registeredUtterance: SpeechSynthesisUtterance | null = null;

    vi.stubGlobal('speechSynthesis', {
      getVoices: vi.fn().mockReturnValue([mockVoice]),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      cancel: vi.fn(),
      resume: vi.fn(),
      speak: vi.fn().mockImplementation((utt: SpeechSynthesisUtterance) => {
        registeredUtterance = utt;
        // Trigger onstart and onend
        setTimeout(() => {
          utt.onstart?.(new Event('start') as SpeechSynthesisEvent);
          utt.onend?.(new Event('end') as SpeechSynthesisEvent);
        }, 10);
      }),
    });

    const onStart = vi.fn();
    const onEnd = vi.fn();

    await speakJarvis('Hello boss, hope you are doing well. How can I help you today?', {
      onStart,
      onEnd,
    });

    expect(window.speechSynthesis.speak).toHaveBeenCalled();
    expect(registeredUtterance).not.toBeNull();
    const actualText = (registeredUtterance as SpeechSynthesisUtterance | null)?.text;
    expect(actualText).toBe('Hello boss, hope you are doing well. How can I help you today?');
    expect(onStart).toHaveBeenCalled();
    expect(onEnd).toHaveBeenCalled();
  });

  it('unlocks speech synthesis on user interaction event', () => {
    const speakMock = vi.fn();
    const resumeMock = vi.fn();
    vi.stubGlobal('speechSynthesis', {
      speak: speakMock,
      resume: resumeMock,
    });

    const onUnlocked = vi.fn();
    const cleanup = unlockSpeechSynthesis(onUnlocked);

    // Simulate user click
    window.dispatchEvent(new Event('click'));

    expect(resumeMock).toHaveBeenCalled();
    expect(speakMock).toHaveBeenCalled();
    expect(onUnlocked).toHaveBeenCalled();

    cleanup();
  });

  it('suppresses duplicate calls for the exact same text within debounce window', async () => {
    const mockVoice = { name: 'Microsoft Ryan Online (Natural) - English (United Kingdom)', lang: 'en-GB' } as SpeechSynthesisVoice;
    let callCount = 0;

    vi.stubGlobal('speechSynthesis', {
      getVoices: vi.fn().mockReturnValue([mockVoice]),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      cancel: vi.fn(),
      resume: vi.fn(),
      speak: vi.fn().mockImplementation((utt: SpeechSynthesisUtterance) => {
        callCount++;
        setTimeout(() => {
          utt.onstart?.(new Event('start') as SpeechSynthesisEvent);
          utt.onend?.(new Event('end') as SpeechSynthesisEvent);
        }, 10);
      }),
    });

    await speakJarvis('Testing duplicate voice suppression');
    // Immediate second call with identical text must be suppressed
    await speakJarvis('Testing duplicate voice suppression');

    expect(callCount).toBe(1);
  });
});
