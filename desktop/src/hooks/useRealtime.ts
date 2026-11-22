/**
 * useRealtime Hook - WebRTC Connection Lifecycle, Bounded Reconnect & Duration Tracking
 * Supports both Google Gemini Live (WebSocket) and OpenAI Realtime (WebRTC).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createGeminiLiveConnection,
  createRealtimePeerConnection,
  fetchVoiceSession,
  type RealtimeConnection,
  type VoiceSessionResponse,
} from '../lib/realtime';
import { recordSessionUsage } from '../lib/api';
import type { OrbState } from '../components/AssistantOrb';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

export interface UseRealtimeReturn {
  connectionStatus: ConnectionStatus;
  orbState: OrbState;
  isMuted: boolean;
  hasMicPermission: boolean | null;
  audioLevel: number;
  errorMessage: string | null;
  sessionData: VoiceSessionResponse | null;
  sessionDuration: number;
  reconnectAttempts: number;
  startSession: () => Promise<void>;
  disconnectSession: () => void;
  toggleMute: () => void;
  interruptSpeech: () => void;
}

export interface UseRealtimeOptions {
  onMessageReceived?: (msg: { sender: 'user' | 'assistant'; text: string }) => void;
}

const MAX_RECONNECT_ATTEMPTS = 3;

export function useRealtime(options?: UseRealtimeOptions): UseRealtimeReturn {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [orbState, setOrbState] = useState<OrbState>('idle');
  const [isMuted, setIsMuted] = useState(false);
  const [hasMicPermission, setHasMicPermission] = useState<boolean | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<VoiceSessionResponse | null>(null);
  const [sessionDuration, setSessionDuration] = useState<number>(0);
  const [reconnectAttempts, setReconnectAttempts] = useState<number>(0);

  const connectionRef = useRef<RealtimeConnection | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const durationTimerRef = useRef<number | null>(null);
  const durationCounterRef = useRef<number>(0);
  const userInitiatedCloseRef = useRef<boolean>(false);

  // Clean up all media tracks and connections
  const cleanupResources = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }

    if (durationTimerRef.current) {
      clearInterval(durationTimerRef.current);
      durationTimerRef.current = null;
    }

    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }

    if (connectionRef.current) {
      if (typeof connectionRef.current.close === 'function') {
        connectionRef.current.close();
      } else {
        const conn = connectionRef.current;
        conn.localStream?.getTracks?.().forEach((track) => track.stop());
        try {
          if (conn.dc && (conn.dc.readyState === 'open' || conn.dc.readyState === 'connecting')) {
            conn.dc.close();
          }
        } catch {
          // ignore
        }
        conn.pc?.close?.();
        if (conn.audioEl) conn.audioEl.srcObject = null;
        if (conn.ws && (conn.ws.readyState === WebSocket.OPEN || conn.ws.readyState === WebSocket.CONNECTING)) {
          conn.ws.close();
        }
      }
      connectionRef.current = null;
    }

    // Report elapsed session duration to budget service
    const duration = durationCounterRef.current;
    durationCounterRef.current = 0;
    recordSessionUsage(duration).catch(() => {});

    setAudioLevel(0);
  }, []);

  // Monitor microphone volume for audio visualizer
  const setupAudioAnalyzer = (stream: MediaStream) => {
    try {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx();
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioCtx;
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const updateVolume = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(1, avg / 80);
        setAudioLevel(normalized);

        animFrameRef.current = requestAnimationFrame(updateVolume);
      };

      updateVolume();
    } catch {
      // AudioContext unavailable in test/headless environment
    }
  };

  const startDurationTimer = () => {
    if (durationTimerRef.current) clearInterval(durationTimerRef.current);
    durationTimerRef.current = window.setInterval(() => {
      durationCounterRef.current += 1;
      setSessionDuration(durationCounterRef.current);
    }, 1000);
  };

  // Start voice session (Gemini or OpenAI)
  const startSession = useCallback(async () => {
    cleanupResources();
    userInitiatedCloseRef.current = false;
    setConnectionStatus('connecting');
    setOrbState('thinking');
    setErrorMessage(null);
    setSessionDuration(0);
    durationCounterRef.current = 0;

    try {
      // 1. Fetch ephemeral client credential from FastAPI backend
      const session = await fetchVoiceSession();
      setSessionData(session);
      setReconnectAttempts(0);

      // 2. Route by provider
      if (session.provider === 'gemini') {
        const conn = await createGeminiLiveConnection(session, {
          onOpen: () => {
            setConnectionStatus('connected');
            setOrbState('listening');
            startDurationTimer();
          },
          onMessage: (data) => {
            const type = data.type as string;
            switch (type) {
              case 'user_transcript':
                if (data.text) {
                  options?.onMessageReceived?.({ sender: 'user', text: data.text as string });
                }
                break;
              case 'input_audio_buffer.speech_started':
                setOrbState('listening');
                break;
              case 'input_audio_buffer.speech_stopped':
                setOrbState('thinking');
                break;
              case 'response.audio.delta':
              case 'response.audio_transcript.delta':
                setOrbState('speaking');
                break;
              case 'response.done':
                if (data.text) {
                  options?.onMessageReceived?.({ sender: 'assistant', text: data.text as string });
                }
                break;
              case 'response.audio.done':
                setOrbState('listening');
                break;
              case 'error':
                setOrbState('error');
                const errObj = data.error as Record<string, string> | undefined;
                setErrorMessage(errObj?.message || 'Google Gemini session error');
                break;
              default:
                break;
            }
          },
          onError: (err) => {
            if (!userInitiatedCloseRef.current) {
              setErrorMessage(err.message || 'Gemini connection error');
              setConnectionStatus('error');
              setOrbState('error');
            }
          },
          onClose: () => {
            if (!userInitiatedCloseRef.current) {
              setConnectionStatus('disconnected');
              setOrbState('disconnected');
            }
          },
        });

        connectionRef.current = conn;
        setHasMicPermission(true);
        setupAudioAnalyzer(conn.localStream);
        setConnectionStatus('connected');
        setOrbState('listening');
        startDurationTimer();
      } else {
        // OpenAI WebRTC
        const conn = await createRealtimePeerConnection(session);
        connectionRef.current = conn;
        setHasMicPermission(true);

        if (conn.dc) {
          conn.dc.onopen = () => {
            setConnectionStatus('connected');
            setOrbState('listening');
            startDurationTimer();
          };

          conn.dc.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              switch (data.type) {
                case 'input_audio_buffer.speech_started':
                  setOrbState('listening');
                  break;
                case 'input_audio_buffer.speech_stopped':
                  setOrbState('thinking');
                  break;
                case 'conversation.item.input_audio_transcription.completed':
                  if (data.transcript) {
                    options?.onMessageReceived?.({ sender: 'user', text: data.transcript as string });
                  }
                  break;
                case 'response.audio.delta':
                case 'response.audio_transcript.delta':
                  setOrbState('speaking');
                  break;
                case 'response.audio_transcript.done':
                  if (data.transcript) {
                    options?.onMessageReceived?.({ sender: 'assistant', text: data.transcript as string });
                  }
                  break;
                case 'response.done':
                  setOrbState('listening');
                  {
                    const respTranscript =
                      data.response?.output?.[0]?.content?.[0]?.transcript ||
                      data.response?.output?.[0]?.content?.[0]?.text;
                    if (respTranscript) {
                      options?.onMessageReceived?.({ sender: 'assistant', text: respTranscript as string });
                    }
                  }
                  break;
                case 'error':
                  setOrbState('error');
                  setErrorMessage(data.error?.message || 'OpenAI Realtime session error');
                  break;
                default:
                  break;
              }
            } catch {
              // Ignore non-json
            }
          };
        }

        if (conn.pc) {
          conn.pc.onconnectionstatechange = () => {
            const state = conn.pc?.connectionState;
            if (state === 'failed' || state === 'disconnected') {
              if (!userInitiatedCloseRef.current) {
                setReconnectAttempts((prev) => {
                  if (prev < MAX_RECONNECT_ATTEMPTS) {
                    setConnectionStatus('reconnecting');
                    setOrbState('thinking');
                    setTimeout(() => {
                      startSession();
                    }, (prev + 1) * 1500);
                    return prev + 1;
                  } else {
                    setConnectionStatus('error');
                    setOrbState('error');
                    setErrorMessage('Voice connection lost. Maximum reconnect attempts reached.');
                    cleanupResources();
                    return prev;
                  }
                });
              } else {
                setConnectionStatus('disconnected');
                setOrbState('disconnected');
                cleanupResources();
              }
            } else if (state === 'closed') {
              setConnectionStatus('disconnected');
              setOrbState('disconnected');
              cleanupResources();
            }
          };
        }

        setupAudioAnalyzer(conn.localStream);
        setConnectionStatus('connected');
        setOrbState('listening');
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to establish voice session';
      setErrorMessage(msg);
      setConnectionStatus('error');
      setOrbState('error');
      cleanupResources();
    }
  }, [cleanupResources]);

  // Disconnect voice session
  const disconnectSession = useCallback(() => {
    userInitiatedCloseRef.current = true;
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    cleanupResources();
    setConnectionStatus('disconnected');
    setOrbState('idle');
    setErrorMessage(null);
  }, [cleanupResources]);

  // Toggle Mute
  const toggleMute = useCallback(() => {
    if (connectionRef.current) {
      const audioTracks = connectionRef.current.localStream.getAudioTracks();
      audioTracks.forEach((track) => {
        track.enabled = isMuted;
      });
      setIsMuted(!isMuted);
    }
  }, [isMuted]);

  // Interruption
  const interruptSpeech = useCallback(() => {
    if (connectionRef.current) {
      connectionRef.current.interrupt?.();
      setOrbState('listening');
    }
  }, []);

  // Release media tracks on unmount
  useEffect(() => {
    return () => {
      cleanupResources();
    };
  }, [cleanupResources]);

  return {
    connectionStatus,
    orbState,
    isMuted,
    hasMicPermission,
    audioLevel,
    errorMessage,
    sessionData,
    sessionDuration,
    reconnectAttempts,
    startSession,
    disconnectSession,
    toggleMute,
    interruptSpeech,
  };
}
