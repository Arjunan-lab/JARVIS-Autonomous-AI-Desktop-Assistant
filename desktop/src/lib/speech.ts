/**
 * JARVIS Speech Synthesis & Wake Word Detection Engine
 * High corporate standard vocalization and passive wake-word recognition.
 */

// Format text for natural spoken dialogue (strip code brackets, markdown, json)
export function sanitizeTextForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, 'Code block omitted.')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/[*_#~]/g, '')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\{[^}]+\}/g, '')
    .replace(/https?:\/\/\S+/g, 'link')
    .replace(/\s+/g, ' ')
    .trim();
}

let preferredVoice: SpeechSynthesisVoice | null = null;
let lastSpokenText = '';
let lastSpokenTimestamp = 0;
let activeAudio: HTMLAudioElement | null = null;

export function ensureVoicesLoaded(): Promise<SpeechSynthesisVoice[]> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      resolve([]);
      return;
    }
    const current = window.speechSynthesis.getVoices();
    if (current && current.length > 0) {
      resolve(current);
      return;
    }

    let resolved = false;
    const onVoices = () => {
      if (resolved) return;
      resolved = true;
      if (window.speechSynthesis) {
        window.speechSynthesis.removeEventListener('voiceschanged', onVoices);
      }
      resolve(window.speechSynthesis?.getVoices() || []);
    };

    window.speechSynthesis.addEventListener('voiceschanged', onVoices);
    // Timeout fallback after 350ms if voiceschanged event does not fire
    setTimeout(() => {
      if (!resolved) {
        resolved = true;
        if (window.speechSynthesis) {
          window.speechSynthesis.removeEventListener('voiceschanged', onVoices);
          resolve(window.speechSynthesis.getVoices());
        } else {
          resolve([]);
        }
      }
    }, 350);
  });
}

function resolveBestVoice(): SpeechSynthesisVoice | null {
  if (typeof window === 'undefined' || !window.speechSynthesis) return null;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return null;

  // Filter out feminine or high-pitched voices to maintain an authentic, deep, bold JARVIS persona
  const isFemale = (v: SpeechSynthesisVoice) =>
    /\b(female|zira|susan|hazel|heera|catherine|jenny|aria|sonia|libby|mia|natasha|clara|victoria|karen|samantha)\b/i.test(
      v.name
    );

  // Tier 1: Bold, natural-flow British male voices (Ryan Natural, Arthur Natural, Oliver Natural, Google UK Male)
  const tier1 = voices.find(
    (v) =>
      !isFemale(v) &&
      (v.lang.startsWith('en-GB') || v.lang === 'en_GB') &&
      (/\b(natural|online)\b/i.test(v.name) || /ryan|arthur|oliver|george|uk english male/i.test(v.name))
  );
  if (tier1) return tier1;

  // Tier 2: Bold, authoritative US/Global natural male voices (Guy Natural, Christopher Natural, Brian Natural)
  const tier2 = voices.find(
    (v) =>
      !isFemale(v) &&
      /\b(natural|online)\b/i.test(v.name) &&
      /guy|christopher|brian|eric|steffan/i.test(v.name)
  );
  if (tier2) return tier2;

  // Tier 3: Any English Natural / Neural male voice
  const tier3 = voices.find(
    (v) => !isFemale(v) && /\b(natural|neural|online)\b/i.test(v.name) && v.lang.startsWith('en')
  );
  if (tier3) return tier3;

  // Tier 4: Any distinguished British male voice
  const tier4 = voices.find(
    (v) => !isFemale(v) && (v.lang.startsWith('en-GB') || v.lang === 'en_GB')
  );
  if (tier4) return tier4;

  // Tier 5: Standard deep male voices (David, Mark, George)
  const tier5 = voices.find(
    (v) => !isFemale(v) && /david|mark|george/i.test(v.name) && v.lang.startsWith('en')
  );
  if (tier5) return tier5;

  // Fallback: First male English voice or first English voice
  return voices.find((v) => !isFemale(v) && v.lang.startsWith('en')) || voices.find((v) => v.lang.startsWith('en')) || voices[0] || null;
}

if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    preferredVoice = resolveBestVoice();
  };
}

export interface SpeakOptions {
  onStart?: () => void;
  onEnd?: () => void;
  rate?: number;
  pitch?: number;
}

/**
 * Primary Voice Engine: Streams high-fidelity, fluent British English audio
 * using Microsoft Edge Neural TTS (en-GB-RyanNeural) to match Paul Bettany's iconic JARVIS.
 */
async function speakViaNeuralBackend(cleanText: string, options?: SpeakOptions): Promise<boolean> {
  if (typeof window === 'undefined' || typeof Audio === 'undefined') return false;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 6000);

    const response = await fetch('/api/voice/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: cleanText,
        voice: 'en-GB-RyanNeural', // Cultured, liberal, fluent British JARVIS voice
        rate: '-3%',               // Measured, sophisticated, fluent cadence
        pitch: '-2Hz',              // Confident British baritone
      }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!response.ok) return false;

    const blob = await response.blob();
    if (!blob || blob.size < 64) return false;

    const audioUrl = URL.createObjectURL(blob);
    const audio = new Audio(audioUrl);
    activeAudio = audio;

    return new Promise((resolve) => {
      audio.onplay = () => {
        options?.onStart?.();
      };
      audio.onended = () => {
        options?.onEnd?.();
        URL.revokeObjectURL(audioUrl);
        if (activeAudio === audio) activeAudio = null;
        resolve(true);
      };
      audio.onerror = () => {
        options?.onEnd?.();
        URL.revokeObjectURL(audioUrl);
        if (activeAudio === audio) activeAudio = null;
        resolve(false);
      };
      audio.play().catch(() => {
        URL.revokeObjectURL(audioUrl);
        if (activeAudio === audio) activeAudio = null;
        resolve(false);
      });
    });
  } catch {
    return false;
  }
}

/**
 * Secondary Local Fallback: Web Speech API synthesis
 */
function speakViaWebSpeech(clean: string, options?: SpeakOptions): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      resolve();
      return;
    }

    ensureVoicesLoaded().then((voices) => {
      try {
        window.speechSynthesis.cancel();
        window.speechSynthesis.resume();

        const utterance = new SpeechSynthesisUtterance(clean);
        // Bold, natural flow cadence
        utterance.rate = options?.rate ?? 0.98;
        utterance.pitch = options?.pitch ?? 0.92;
        utterance.volume = 1.0;

        if (!preferredVoice && voices.length > 0) {
          preferredVoice = resolveBestVoice();
        }
        if (preferredVoice) {
          utterance.voice = preferredVoice;
        }

        utterance.onstart = () => {
          options?.onStart?.();
        };

        utterance.onend = () => {
          options?.onEnd?.();
          resolve();
        };

        utterance.onerror = () => {
          options?.onEnd?.();
          resolve();
        };

        // Small tick to ensure cancel() has cleanly settled in Chromium
        setTimeout(() => {
          try {
            window.speechSynthesis.speak(utterance);
            window.speechSynthesis.resume();
          } catch {
            options?.onEnd?.();
            resolve();
          }
        }, 16);
      } catch {
        options?.onEnd?.();
        resolve();
      }
    });
  });
}

function stopActiveAudioPlayback(): void {
  if (activeAudio) {
    try {
      activeAudio.pause();
      activeAudio.currentTime = 0;
    } catch {
      // ignore
    }
    activeAudio = null;
  }
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    try {
      window.speechSynthesis.cancel();
    } catch {
      // ignore
    }
  }
}

export async function speakJarvis(text: string, options?: SpeakOptions): Promise<void> {
  const clean = sanitizeTextForSpeech(text);
  if (!clean) return;

  // Suppress rapid duplicate vocalizations of the exact same text within 2 seconds
  const now = Date.now();
  if (clean === lastSpokenText && now - lastSpokenTimestamp < 2000) {
    return;
  }

  stopActiveAudioPlayback();
  lastSpokenText = clean;
  lastSpokenTimestamp = now;

  // 1. Try high-fidelity British Neural JARVIS voice (en-GB-RyanNeural)
  const neuralSuccess = await speakViaNeuralBackend(clean, options);
  if (neuralSuccess) return;

  // 2. Fall back to local Web Speech API synthesis
  return speakViaWebSpeech(clean, options);
}

export function stopJarvisSpeech(): void {
  lastSpokenText = '';
  lastSpokenTimestamp = 0;
  stopActiveAudioPlayback();
}

/**
 * Autoplay unlocker: ensures speech can be synthesized after initial user gesture
 */
export function unlockSpeechSynthesis(onUnlocked?: () => void): () => void {
  if (typeof window === 'undefined') return () => {};

  let unlocked = false;

  const unlockHandler = () => {
    if (unlocked) return;
    unlocked = true;

    if (activeAudio && activeAudio.paused) {
      try {
        activeAudio.play();
      } catch {
        // ignore
      }
    }

    // Trigger an empty utterance and resume to unlock the Web Speech synthesis engine
    if (window.speechSynthesis) {
      try {
        window.speechSynthesis.resume();
        const dummy = new SpeechSynthesisUtterance('');
        window.speechSynthesis.speak(dummy);
      } catch {
        // ignore
      }
    }

    onUnlocked?.();
    cleanup();
  };

  const cleanup = () => {
    window.removeEventListener('click', unlockHandler);
    window.removeEventListener('keydown', unlockHandler);
    window.removeEventListener('pointerdown', unlockHandler);
    window.removeEventListener('touchstart', unlockHandler);
  };

  window.addEventListener('click', unlockHandler, { once: true, passive: true });
  window.addEventListener('keydown', unlockHandler, { once: true, passive: true });
  window.addEventListener('pointerdown', unlockHandler, { once: true, passive: true });
  window.addEventListener('touchstart', unlockHandler, { once: true, passive: true });

  return cleanup;
}

/**
 * Passive wake word listener for phrases like "Hello JARVIS", "Hey JARVIS", "JARVIS"
 */
export interface WakeWordListener {
  start: () => void;
  stop: () => void;
  isActive: () => boolean;
}

export function createWakeWordListener(onWakeWordDetected: (phrase: string) => void): WakeWordListener {
  if (typeof window === 'undefined') {
    return { start: () => {}, stop: () => {}, isActive: () => false };
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const SpeechRecognitionClass =
    (window as unknown as { SpeechRecognition?: any; webkitSpeechRecognition?: any }).SpeechRecognition ||
    (window as unknown as { webkitSpeechRecognition?: any }).webkitSpeechRecognition;

  if (!SpeechRecognitionClass) {
    return { start: () => {}, stop: () => {}, isActive: () => false };
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let recognition: any = null;
  let running = false;
  let restartTimeout: number | null = null;

  const WAKE_PATTERNS = [
    /\b(?:hello|hey|hi|ok|okay)\s+jarvis\b/i,
    /\bjarvis\s+(?:wake\s*up|listen|are\s+you\s+there)\b/i,
    /\b(?:hello|hey)\s+java\b/i, // common phonetic mistranscription by SpeechRecognition
    /\bjarvis\b/i,
  ];

  const initRecognition = () => {
    if (recognition) return;
    try {
      recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      recognition.onresult = (event: any) => {
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcript = event.results[i][0]?.transcript || '';
          const trimmed = transcript.trim().toLowerCase();

          for (const pattern of WAKE_PATTERNS) {
            if (pattern.test(trimmed)) {
              onWakeWordDetected(trimmed);
              return;
            }
          }
        }
      };

      recognition.onerror = () => {
        // Continue listening on minor network or speech errors
      };

      recognition.onend = () => {
        if (running) {
          restartTimeout = window.setTimeout(() => {
            if (running && recognition) {
              try {
                recognition.start();
              } catch {
                // Ignore start collisions
              }
            }
          }, 400);
        }
      };
    } catch {
      // Headless / unsupported fallback
    }
  };

  return {
    start: () => {
      if (running) return;
      running = true;
      initRecognition();
      if (recognition) {
        try {
          recognition.start();
        } catch {
          // Ignore if already started
        }
      }
    },
    stop: () => {
      running = false;
      if (restartTimeout) {
        clearTimeout(restartTimeout);
        restartTimeout = null;
      }
      if (recognition) {
        try {
          recognition.stop();
        } catch {
          // ignore
        }
      }
    },
    isActive: () => running,
  };
}
