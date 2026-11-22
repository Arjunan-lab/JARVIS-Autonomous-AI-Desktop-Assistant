import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  AppWindow,
  Brain,
  CheckSquare,
  ChevronRight,
  Database,
  Menu,
  MessageSquare,
  Mic,
  Server,
  Settings,
  Shield,
  Square,
} from 'lucide-react';
import { executeCommand, fetchApprovals, fetchHealth, type HealthResponse } from './lib/api';
import {
  createWakeWordListener,
  speakJarvis,
  unlockSpeechSynthesis,
  type WakeWordListener,
} from './lib/speech';
import { AssistantOrb, type OrbState } from './components/AssistantOrb';
import { ConversationPanel, type Message } from './components/ConversationPanel';
import { TaskPanel } from './components/TaskPanel';
import { MemoryPanel } from './components/MemoryPanel';
import { ApprovalDialog } from './components/ApprovalDialog';
import { SettingsPanel } from './components/SettingsPanel';
import { ApplicationsPanel } from './components/ApplicationsPanel';
import { useRealtime } from './hooks/useRealtime';
import './App.css';

export const STARTER_VOICEOVER =
  'Hello boss. Hope you are doing well. How can I help you today?';
export const CORPORATE_GREETING = STARTER_VOICEOVER;

// Module-level guard preventing duplicate startup vocalizations across React StrictMode mount cycles
let starterVoiceoverSessionSpoken = false;

export function resetStarterVoiceoverSession(): void {
  starterVoiceoverSessionSpoken = false;
}

type ActiveView = 'assistant' | 'tasks' | 'memory' | 'approvals' | 'apps' | 'settings' | 'architecture';

interface NavItemConfig {
  id: ActiveView;
  label: string;
  icon: React.ReactNode;
}

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [backendStatus, setBackendStatus] = useState<'loading' | 'online' | 'offline'>('loading');
  const [activeTab, setActiveTab] = useState<ActiveView>('assistant');
  const [pendingApprovals, setPendingApprovals] = useState<number>(0);
  const [timeString, setTimeString] = useState<string>('10:24 AM');
  const [typedMessage, setTypedMessage] = useState<string>('');

  // Cinematic Chat Panel & Sphere Transition State
  const [isChatActive, setIsChatActive] = useState<boolean>(false);
  const [activeTypingId, setActiveTypingId] = useState<string | null>(null);
  const [isTypewriting, setIsTypewriting] = useState<boolean>(false);

  // Inactivity Timer Refs
  const inactivityTimerRef = useRef<number | null>(null);
  const isProcessingRef = useRef<boolean>(false);
  const isTypewritingRef = useRef<boolean>(false);
  const typedMessageRef = useRef<string>('');
  const panelDraftRef = useRef<string>('');
  const isChatActiveRef = useRef<boolean>(false);

  // Synchronize refs
  isTypewritingRef.current = isTypewriting;
  typedMessageRef.current = typedMessage;
  isChatActiveRef.current = isChatActive;

  // Inactivity Manager: 15s idle timer that dismisses chat and returns sphere to center
  const resetInactivityTimer = () => {
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
      inactivityTimerRef.current = null;
    }

    if (!isChatActiveRef.current) return;

    inactivityTimerRef.current = window.setTimeout(() => {
      // Check blockers: do not dismiss while typing/generating or while draft text remains
      if (
        isProcessingRef.current ||
        isTypewritingRef.current ||
        typedMessageRef.current.trim().length > 0 ||
        panelDraftRef.current.trim().length > 0
      ) {
        resetInactivityTimer();
        return;
      }

      // Inactivity timeout: dismiss panel and glide sphere back to center
      setIsChatActive(false);
    }, 15000);
  };

  const realtime = useRealtime({
    onMessageReceived: (msg) => {
      const newMsg: Message = {
        id: `voice-${Date.now()}-${Math.random()}`,
        sender: msg.sender,
        text: msg.text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, newMsg]);

      // If assistant voice transcript, activate typewriter and chat window
      if (msg.sender === 'assistant') {
        setActiveTypingId(newMsg.id);
        setIsTypewriting(true);
      }
      setIsChatActive(true);
      resetInactivityTimer();
    },
  });

  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: STARTER_VOICEOVER,
      timestamp: 'Just now',
    },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  isProcessingRef.current = isProcessing;

  const wakeWordListenerRef = useRef<WakeWordListener | null>(null);

  // Initial launch and page refresh starter communication voiceover
  useEffect(() => {
    const playStarterVoiceover = () => {
      if (starterVoiceoverSessionSpoken) return;
      starterVoiceoverSessionSpoken = true;

      speakJarvis(STARTER_VOICEOVER, {
        onStart: () => {
          setIsTypewriting(true);
        },
        onEnd: () => {
          setIsTypewriting(false);
        },
      }).catch(() => {
        // Autoplay policy may delay vocalization until user gesture
      });
    };

    // 1. Immediately attempt to speak on initial launch or page refresh
    playStarterVoiceover();

    // 2. Set up unlocker so if browser autoplay policy blocked the immediate call,
    // the user's first interaction (click/tap/key) plays the starter voiceover
    const cleanupUnlock = unlockSpeechSynthesis(() => {
      if (!starterVoiceoverSessionSpoken) {
        playStarterVoiceover();
      }
    });

    return () => {
      cleanupUnlock();
    };
  }, []);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
      wakeWordListenerRef.current?.stop();
    };
  }, []);

  // When chat activates, start inactivity countdown
  useEffect(() => {
    if (isChatActive) {
      resetInactivityTimer();
    }
  }, [isChatActive]);

  // Live Clock
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeString(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    };
    updateTime();
    const timer = setInterval(updateTime, 10000);
    return () => clearInterval(timer);
  }, []);

  // Poll backend health & approvals
  const checkBackendHealth = async () => {
    setBackendStatus('loading');
    try {
      const data = await fetchHealth();
      setHealth(data);
      setBackendStatus('online');
    } catch {
      setBackendStatus('offline');
    }
  };

  const checkPendingApprovals = async () => {
    try {
      const data = await fetchApprovals('pending');
      setPendingApprovals(data.pending_count);
    } catch {
      // Non-blocking
    }
  };

  useEffect(() => {
    checkBackendHealth();
    checkPendingApprovals();
    const interval = setInterval(() => {
      checkBackendHealth();
      checkPendingApprovals();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  // Compute effective orb state with subtle reactions to processing and typewriter communication
  const effectiveOrbState: OrbState =
    backendStatus === 'offline'
      ? 'disconnected'
      : isProcessing
      ? 'thinking'
      : isTypewriting
      ? 'speaking'
      : realtime.connectionStatus === 'connected'
      ? realtime.orbState
      : realtime.orbState === 'error'
      ? 'error'
      : 'idle';

  const isVoiceActive =
    realtime.connectionStatus === 'connected' || realtime.connectionStatus === 'connecting';

  // Passive background wake-word listener (detects "Hello JARVIS" to auto-activate voice session)
  useEffect(() => {
    if (!isVoiceActive) {
      if (!wakeWordListenerRef.current) {
        wakeWordListenerRef.current = createWakeWordListener(async (phrase) => {
          setIsChatActive(true);
          resetInactivityTimer();

          const wakeReply =
            'At your service, sir. Voice assistance interface activated. I am listening continuously and standing by for your live inquiries.';
          const wakeMsg: Message = {
            id: `wake-${Date.now()}`,
            sender: 'assistant',
            text: `[Voice Wake: "${phrase}"] ${wakeReply}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          };

          setMessages((prev) => [...prev, wakeMsg]);
          setActiveTypingId(wakeMsg.id);
          setIsTypewriting(true);

          await speakJarvis(wakeReply);
          await realtime.startSession();
        });
      }
      wakeWordListenerRef.current.start();
    } else {
      wakeWordListenerRef.current?.stop();
    }

    return () => {
      wakeWordListenerRef.current?.stop();
    };
  }, [isVoiceActive]);

  const handleToggleVoice = async () => {
    if (isVoiceActive) {
      realtime.disconnectSession();
    } else {
      await realtime.startSession();
    }
  };

  const handleSendMessage = async (text: string) => {
    setIsChatActive(true);
    resetInactivityTimer();

    const userMsg: Message = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    const trimmed = text.trim();
    const isHelloJarvis =
      /^(?:hello|hey|hi|ok|okay)\s+jarvis[!.?]*$/i.test(trimmed) ||
      /^jarvis\s*(?:wake\s*up|listen|are\s+you\s+there)?[!.?]*$/i.test(trimmed);

    if (isHelloJarvis) {
      const wakeReply =
        'At your service, sir. Voice assistance interface activated. I am listening continuously and standing by for your live inquiries.';
      const assistantMsg: Message = {
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        text: wakeReply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setActiveTypingId(assistantMsg.id);
      setIsTypewriting(true);
      setIsProcessing(false);
      resetInactivityTimer();

      // Vocalize response and automatically activate live voice session
      speakJarvis(wakeReply, {
        onEnd: async () => {
          if (!isVoiceActive) {
            await realtime.startSession();
          }
        },
      });
      return;
    }

    try {
      const opResult = await executeCommand(text);

      const toolCalls: Message['toolCalls'] = opResult.step_results?.map((step) => ({
        name: step.action_type,
        status:
          step.status === 'completed'
            ? 'success'
            : step.status === 'failed' || step.status === 'cancelled'
            ? 'failed'
            : step.status === 'awaiting_approval'
            ? 'requires_approval'
            : 'pending',
        details: step.message || undefined,
      }));

      let reply = '';
      if (opResult.status === 'completed') {
        const stepMessages = opResult.step_results
          ?.map((s) => s.message)
          .filter(Boolean) || [];

        const calcStep = opResult.step_results?.find((s) => s.action_type === 'calculate');
        const calcRes = calcStep?.evidence?.result;

        if (calcStep && calcRes !== undefined) {
          const expr = calcStep.evidence?.expression || '';
          reply = `I have opened Calculator and completed the calculation for you, sir: ${expr} = ${calcRes}.`;
        } else if (stepMessages.length > 0) {
          reply = stepMessages.join('. ') + '.';
        } else {
          const targetStr = opResult.target_app_name || opResult.target_app_id ? ` for ${opResult.target_app_name || opResult.target_app_id}` : '';
          reply = `Operation completed successfully${targetStr}.`;
        }
      } else if (opResult.status === 'awaiting_approval') {
        reply = `Operation paused. Approval required: ${opResult.error_message || 'Protected operation requested.'}`;
      } else {
        reply = `Operation ${opResult.status}: ${opResult.error_message || opResult.message || 'Execution stopped.'}`;
      }

      const assistantMsg: Message = {
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        text: reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        toolCalls: toolCalls && toolCalls.length > 0 ? toolCalls : undefined,
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setActiveTypingId(assistantMsg.id);
      setIsTypewriting(true);

      // Vocalize response so user receives both text and spoken voice output
      speakJarvis(reply);
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown communication error';
      const assistantMsg: Message = {
        id: `ast-${Date.now()}`,
        sender: 'assistant',
        text: `Command execution failed: ${errorMsg}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        toolCalls: [{ name: 'execute_command', status: 'failed', details: errorMsg }],
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setActiveTypingId(assistantMsg.id);
      setIsTypewriting(true);

      speakJarvis(`Command execution failed: ${errorMsg}`);
    } finally {
      setIsProcessing(false);
      resetInactivityTimer();
    }
  };

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!typedMessage.trim() || isProcessing) return;
    handleSendMessage(typedMessage.trim());
    setTypedMessage('');
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const contextualSubtitle = () => {
    if (backendStatus === 'offline') return 'SYSTEM OFFLINE · CHECK LOCAL BACKEND SERVICE';
    if (effectiveOrbState === 'listening') return 'LISTENING · AUDIO STREAM ACTIVE';
    if (effectiveOrbState === 'thinking') return 'SYNTHESIZING NEURAL INFERENCE...';
    if (effectiveOrbState === 'speaking') return 'TRANSMITTING VOCAL SYNTHESIS...';
    if (effectiveOrbState === 'error') return 'COMMUNICATION INTERRUPTED';
    return 'HOW CAN I HELP YOU TODAY?';
  };

  const navItems: NavItemConfig[] = [
    { id: 'assistant', label: 'Assistant Cockpit', icon: <MessageSquare size={18} /> },
    { id: 'tasks', label: 'Tasks & Reminders', icon: <CheckSquare size={18} /> },
    { id: 'memory', label: 'Memory & Knowledge', icon: <Brain size={18} /> },
    { id: 'approvals', label: 'Approvals & Audit', icon: <Shield size={18} /> },
    { id: 'apps', label: 'App Permissions', icon: <AppWindow size={18} /> },
    { id: 'settings', label: 'Settings & Budget', icon: <Settings size={18} /> },
    { id: 'architecture', label: 'Architecture & Data', icon: <Server size={18} /> },
  ];

  return (
    <div className="jarvis-app">
      {/* ── Top Bar ────────────────────────────────────────────── */}
      <header className="jarvis-topbar">
        <div className="topbar-left">
          {/* Segmented Arc Reactor Icon */}
          <div className="topbar-reactor-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
              <circle
                cx="12"
                cy="12"
                r="9"
                stroke="#FF3038"
                strokeWidth="1.75"
                strokeDasharray="42 9"
                strokeLinecap="round"
              />
              <circle cx="12" cy="12" r="2.8" fill="#FF3038" />
            </svg>
          </div>
          <span className="topbar-brand">JARVIS</span>
        </div>

        <div className="topbar-right">
          {/* System status matching test contract */}
          <div className="system-status-indicator">
            <span className={`status-dot ${backendStatus}`} />
            <span className="status-label">
              {backendStatus === 'online' ? 'SYSTEM ONLINE' : 'SYSTEM OFFLINE'}
            </span>
            <span className="status-meta">
              {backendStatus === 'online' && ` · Backend Online (v${health?.version ?? '0.1.0'})`}
              {backendStatus === 'loading' && ' · Connecting...'}
              {backendStatus === 'offline' && ' · Backend Offline'}
            </span>
          </div>

          <div className="topbar-clock">{timeString}</div>

          {/* Minimal hairline window controls */}
          <div className="window-controls">
            <button type="button" className="window-btn min" aria-label="Minimize">
              —
            </button>
            <button type="button" className="window-btn close" aria-label="Close">
              ✕
            </button>
          </div>
        </div>
      </header>

      {/* ── Main Container: Nav Rail + Main View ────────────────── */}
      <div className="jarvis-body">
        {/* Narrow Icon-only Left Rail */}
        <aside className="jarvis-rail" aria-label="Navigation rail">
          <div className="rail-nav-group">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`rail-item ${activeTab === item.id ? 'active' : ''}`}
                onClick={() => {
                  if (item.id === 'assistant') {
                    if (activeTab === 'assistant') {
                      setIsChatActive((prev) => !prev);
                      resetInactivityTimer();
                    } else {
                      setActiveTab('assistant');
                    }
                  } else {
                    setActiveTab(item.id);
                  }
                }}
                aria-label={item.label}
                aria-current={activeTab === item.id ? 'page' : undefined}
                title={item.label}
              >
                <span className="rail-icon">{item.icon}</span>
                {/* Accessible text for test contracts and tooltips */}
                <span className="rail-label-text">{item.label}</span>
                {item.id === 'approvals' && pendingApprovals > 0 && (
                  <span className="rail-badge">{pendingApprovals}</span>
                )}
              </button>
            ))}
          </div>

          <div className="rail-footer">
            <button type="button" className="rail-item menu-trigger" aria-label="Menu" title="Menu">
              <Menu size={18} />
            </button>
          </div>
        </aside>

        {/* ── Stage Area ─────────────────────────────────────────── */}
        <main className="jarvis-stage">
          {/* Realtime Error Banner */}
          {realtime.errorMessage && (
            <div className="alert-banner">
              <AlertTriangle size={15} />
              <span>{realtime.errorMessage}</span>
              <button
                type="button"
                className="alert-dismiss"
                onClick={() => realtime.disconnectSession()}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* ── Assistant View (Home Screen) ────────────────────── */}
          {activeTab === 'assistant' && (
            <div className="cinematic-home">
              {/* HUD Telemetry Card (floating right as in reference image, fades out when chat is active) */}
              <div className={`hud-telemetry-card ${isChatActive ? 'hidden' : ''}`}>
                <div className="telemetry-row active">
                  <span className="telemetry-dot red" />
                  <span className="telemetry-label">INTEGRATING SYSTEMS</span>
                </div>
                <div className="telemetry-row">
                  <span className="telemetry-dot dim" />
                  <span className="telemetry-label">MONITORING</span>
                </div>
                <div className="telemetry-row active">
                  <span className="telemetry-dot red" />
                  <span className="telemetry-label">READY</span>
                </div>
              </div>

              {/* Central Neural Orb Area with smooth transition between center & left */}
              <div className={`neural-core-centerpiece ${isChatActive ? 'chat-active' : ''}`}>
                <AssistantOrb
                  state={effectiveOrbState}
                  audioLevel={realtime.audioLevel}
                  onClick={handleToggleVoice}
                  subtitle={contextualSubtitle()}
                />
              </div>

              {/* Translucent Futuristic HUD Chat Panel (Matching Reference Image) */}
              <div
                className={`cinematic-chat-panel ${isChatActive ? 'visible' : ''}`}
                onMouseMove={resetInactivityTimer}
                onClick={resetInactivityTimer}
              >
                <ConversationPanel
                  messages={messages}
                  onSendMessage={handleSendMessage}
                  isLoading={isProcessing}
                  onClearHistory={() => setMessages([])}
                  onUserInteraction={resetInactivityTimer}
                  onTypewritingChange={(typing) => {
                    setIsTypewriting(typing);
                    if (!typing) resetInactivityTimer();
                  }}
                  onDraftChange={(draft) => {
                    panelDraftRef.current = draft;
                    resetInactivityTimer();
                  }}
                  activeAssistantTypingId={activeTypingId}
                />
              </div>

              {/* Bottom Controls Row */}
              <div className="bottom-controls-bar">
                {/* Left: Voice Mode capsule button */}
                <button
                  type="button"
                  className={`voice-mode-capsule ${isVoiceActive ? 'active' : ''}`}
                  onClick={handleToggleVoice}
                  title={isVoiceActive ? 'Disconnect voice' : 'Start voice mode'}
                >
                  <span className="capsule-dot" />
                  <div className="capsule-texts">
                    <span className="capsule-title">Voice Mode</span>
                    <span className="capsule-sub">
                      {isVoiceActive
                        ? `Connected (${formatDuration(realtime.sessionDuration)})`
                        : 'Press and hold to talk'}
                    </span>
                  </div>
                  <ChevronRight size={14} className="capsule-arrow" />
                </button>

                {/* Center: Glowing red circular mic button with audio waveform ticks */}
                <div className="center-orb-control">
                  <div className="audio-wave-flank left">
                    <span className="wave-tick-line" />
                    <span className="wave-tick-dot" />
                    <span className="wave-tick-dot" />
                    <span className="wave-tick-line" />
                  </div>

                  <button
                    type="button"
                    className={`cinematic-voice-btn ${isVoiceActive ? 'active' : ''}`}
                    onClick={handleToggleVoice}
                    aria-label={isVoiceActive ? 'Stop Voice Mode' : 'Start Voice Mode'}
                    title={isVoiceActive ? 'Disconnect audio stream' : 'Tap to speak'}
                  >
                    {isVoiceActive ? (
                      <Square size={16} fill="currentColor" />
                    ) : (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="voice-node-reticle">
                        <circle cx="12" cy="7.5" r="1.75" fill="#EDEDEF" />
                        <circle cx="7.5" cy="15.5" r="1.75" fill="#EDEDEF" />
                        <circle cx="16.5" cy="15.5" r="1.75" fill="#EDEDEF" />
                      </svg>
                    )}
                  </button>

                  <div className="audio-wave-flank right">
                    <span className="wave-tick-line" />
                    <span className="wave-tick-dot" />
                    <span className="wave-tick-dot" />
                    <span className="wave-tick-line" />
                  </div>

                  <span className="voice-btn-caption">
                    {isVoiceActive ? 'SESSION ACTIVE' : 'TAP TO SPEAK'}
                  </span>
                </div>

                {/* Right: Minimal text composer & Conversation Log trigger */}
                <div className={`composer-container ${isChatActive ? 'chat-open' : ''}`}>
                  <form onSubmit={handleTextSubmit} className="minimal-composer-pill">
                    <input
                      type="text"
                      value={typedMessage}
                      onChange={(e) => {
                        setTypedMessage(e.target.value);
                        if (e.target.value.length > 0 && !isChatActive) {
                          setIsChatActive(true);
                        }
                        resetInactivityTimer();
                      }}
                      onFocus={() => {
                        if (!isChatActive) {
                          setIsChatActive(true);
                        }
                        resetInactivityTimer();
                      }}
                      placeholder="Type a message..."
                      className="composer-input"
                      aria-label="Type message to JARVIS"
                    />
                    <button
                      type="submit"
                      className="composer-send-btn"
                      disabled={!typedMessage.trim() || isProcessing}
                      aria-label="Send message"
                    >
                      <ChevronRight size={14} />
                    </button>
                    {/* Accessible toggle trigger */}
                    <span
                      className="log-label-sr"
                      role="button"
                      tabIndex={0}
                      onClick={() => {
                        setIsChatActive((prev) => !prev);
                        resetInactivityTimer();
                      }}
                      aria-label="Toggle Conversation Log"
                    />
                  </form>
                </div>
              </div>

              {/* Bottom Right Watermark */}
              <div className="cinematic-watermark" aria-hidden="true">
                <span className="watermark-label">A BETTER TOMORROW</span>
                <div className="watermark-accent" />
              </div>
            </div>
          )}

          {/* ── Sub Views (Tasks, Memory, Approvals, Settings, Architecture) ── */}
          {activeTab !== 'assistant' && (
            <div className="subview-container">
              <div className="subview-header">
                <h2 className="subview-title">
                  {navItems.find((n) => n.id === activeTab)?.label}
                </h2>
              </div>
              <div className="subview-content">
                {activeTab === 'tasks' && <TaskPanel />}
                {activeTab === 'memory' && <MemoryPanel />}
                {activeTab === 'approvals' && (
                  <ApprovalDialog onApprovalsUpdated={checkPendingApprovals} />
                )}
                {activeTab === 'apps' && <ApplicationsPanel />}
                {activeTab === 'settings' && <SettingsPanel />}

                {activeTab === 'architecture' && (
                  <div className="architecture-view">
                    <div className="architecture-header card">
                      <div className="stage-title">SYSTEM ARCHITECTURE & VOICE ENGINE</div>
                      <p className="stage-desc">
                        FastAPI control center connected to OpenAI Realtime WebRTC audio gateway with
                        automatic fallback to Google Gemini Live, SQLite local storage with Alembic
                        migrations, and server-side secret isolation.
                      </p>
                    </div>

                    <div className="architecture-grid">
                      <div className="card">
                        <div className="card-header">
                          <div className="card-title">
                            <Mic size={16} />
                            <span>Realtime WebRTC</span>
                          </div>
                          <span
                            className={`card-badge ${
                              realtime.connectionStatus === 'connected' ? 'active' : 'ready'
                            }`}
                          >
                            {realtime.connectionStatus}
                          </span>
                        </div>
                        <p className="card-body">
                          POST /api/voice/session generates temporary client tokens (ek_...). Browser
                          connects directly via WebRTC with zero permanent key exposure.
                        </p>
                      </div>

                      <div className="card">
                        <div className="card-header">
                          <div className="card-title">
                            <Database size={16} />
                            <span>SQLite Persistence</span>
                          </div>
                          <span className="card-badge active">Migrated</span>
                        </div>
                        <p className="card-body">
                          Local relational store running automated Alembic schema migrations for tasks,
                          memories, policies, and audit events.
                        </p>
                      </div>

                      <div className="card">
                        <div className="card-header">
                          <div className="card-title">
                            <Shield size={16} />
                            <span>Security Approvals & Audit</span>
                          </div>
                          <span className="card-badge active">Enforced</span>
                        </div>
                        <p className="card-body">
                          Zero direct client-side OS execution. Sensitive capabilities require explicit
                          user confirmation and are logged to an immutable SQLite audit trail.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
