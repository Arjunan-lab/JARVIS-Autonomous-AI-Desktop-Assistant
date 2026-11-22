import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Trash2,
  Wrench,
} from 'lucide-react';
import { TypewriterText } from './TypewriterText';
import './ConversationPanel.css';

export interface ToolCallItem {
  name: string;
  status: 'pending' | 'success' | 'failed' | 'requires_approval';
  details?: string;
}

export interface Message {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  timestamp: string;
  toolCalls?: ToolCallItem[];
}

interface ConversationPanelProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading?: boolean;
  onClearHistory?: () => void;
  onUserInteraction?: () => void;
  onTypewritingChange?: (isTypewriting: boolean) => void;
  onDraftChange?: (draft: string) => void;
  activeAssistantTypingId?: string | null;
}

export const ConversationPanel: React.FC<ConversationPanelProps> = ({
  messages,
  onSendMessage,
  isLoading = false,
  onClearHistory,
  onUserInteraction,
  onTypewritingChange,
  onDraftChange,
  activeAssistantTypingId,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView?.({
      behavior: smooth ? 'smooth' : 'auto',
      block: 'nearest',
    });
  };

  useEffect(() => {
    scrollToBottom(true);
  }, [messages, isLoading]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    const textToSend = inputText.trim();
    setInputText('');
    onDraftChange?.('');
    onSendMessage(textToSend);
    onUserInteraction?.();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const quickPrompts = [
    'Hello JARVIS',
    'Check system health and core status',
    'List pending tasks for today',
  ];

  return (
    <div
      ref={containerRef}
      className="hud-chat-panel-container"
      onMouseMove={onUserInteraction}
      onClick={onUserInteraction}
      onKeyDown={onUserInteraction}
      onWheel={onUserInteraction}
    >
      {/* ── Illuminated HUD Corner Brackets ────────────────────────── */}
      <div className="hud-corner-bracket corner-tl" aria-hidden="true" />
      <div className="hud-corner-bracket corner-tr" aria-hidden="true" />
      <div className="hud-corner-bracket corner-bl" aria-hidden="true" />
      <div className="hud-corner-bracket corner-br" aria-hidden="true" />

      {/* ── Futuristic Header ──────────────────────────────────────── */}
      <div className="hud-chat-header">
        <div className="hud-header-identity">
          <span className="hud-header-dot" aria-hidden="true" />
          <div className="hud-header-titles">
            <span className="hud-brand-title">J A R V I S</span>
            <div className="hud-role-row">
              <span className="hud-role-indicator" aria-hidden="true" />
              <span className="hud-role-label">AI ASSISTANT</span>
            </div>
          </div>
        </div>

        <div className="hud-header-actions">
          {/* Accessible text for test suites and screen readers */}
          <span className="sr-conversation-log">Conversation Log</span>

          {isLoading && (
            <span className="hud-status-badge">SYNTHESIZING...</span>
          )}

          {onClearHistory && messages.length > 0 && (
            <button
              type="button"
              className="hud-clear-action"
              onClick={onClearHistory}
              title="Clear conversation"
              aria-label="Clear conversation"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* ── Messages Scroll Area ───────────────────────────────────── */}
      <div
        className="hud-chat-messages"
        role="log"
        aria-live="polite"
        onScroll={onUserInteraction}
      >
        {messages.length === 0 ? (
          <div className="hud-empty-state">
            <div className="hud-empty-reactor" aria-hidden="true">
              <svg width="38" height="38" viewBox="0 0 24 24" fill="none">
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                  stroke="#FF3038"
                  strokeWidth="1.5"
                  strokeDasharray="42 8"
                />
                <circle cx="12" cy="12" r="2.8" fill="#FF3038" />
              </svg>
            </div>
            <p className="hud-empty-title">JARVIS CORE ONLINE</p>
            <p className="hud-empty-desc">
              Speak using the neural microphone or submit an instruction below.
            </p>
            <div className="hud-quick-prompts">
              {quickPrompts.map((prompt, i) => (
                <button
                  key={i}
                  type="button"
                  className="hud-prompt-chip"
                  onClick={() => {
                    onSendMessage(prompt);
                    onUserInteraction?.();
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg) => {
            const isAssistant = msg.sender === 'assistant';
            const isUser = msg.sender === 'user';
            const isCurrentlyTyping = isAssistant && msg.id === activeAssistantTypingId;

            return (
              <div
                key={msg.id}
                className={`hud-msg-row ${isAssistant ? 'msg-assistant' : 'msg-user'}`}
              >
                {/* Assistant Segmented Arc Reactor Avatar (Left) */}
                {isAssistant && (
                  <div className="hud-msg-avatar assistant-avatar" aria-hidden="true">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <circle
                        cx="12"
                        cy="12"
                        r="8.5"
                        stroke="#FF3038"
                        strokeWidth="1.8"
                        strokeDasharray="36 8"
                        strokeLinecap="round"
                      />
                      <circle cx="12" cy="12" r="2.6" fill="#FF3038" />
                    </svg>
                  </div>
                )}

                {/* Message Bubble + Meta Column */}
                <div className="hud-msg-column">
                  <div className="hud-msg-card">
                    {isCurrentlyTyping ? (
                      <TypewriterText
                        text={msg.text}
                        isNew={true}
                        charIntervalMs={45}
                        onCharacterTyped={() => scrollToBottom(false)}
                        onComplete={() => onTypewritingChange?.(false)}
                      />
                    ) : (
                      <span className="msg-text-content">{msg.text}</span>
                    )}

                    {/* Tool Calls */}
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="hud-tool-calls">
                        {msg.toolCalls.map((tool, idx) => (
                          <div
                            key={idx}
                            className={`hud-tool-chip status-${tool.status}`}
                          >
                            <Wrench size={11} />
                            <span className="tool-name">{tool.name}</span>
                            {tool.status === 'success' && <CheckCircle2 size={11} />}
                            {tool.status === 'failed' && <AlertCircle size={11} />}
                            {tool.status === 'requires_approval' && (
                              <span className="tool-approval-pill">Approval Required</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Timestamp below card */}
                  <div className="hud-msg-timestamp">
                    <Clock size={10} className="ts-clock-icon" />
                    <span>{msg.timestamp}</span>
                  </div>
                </div>

                {/* User Outline Silhouette Avatar (Right) */}
                {isUser && (
                  <div className="hud-msg-avatar user-avatar" aria-hidden="true">
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#85858D"
                      strokeWidth="1.5"
                    >
                      <circle cx="12" cy="12" r="9.5" />
                      <circle cx="12" cy="9.2" r="3.2" />
                      <path
                        d="M6.2 18c1.3-2.6 3.4-3.4 5.8-3.4s4.5.8 5.8 3.4"
                        strokeLinecap="round"
                      />
                    </svg>
                  </div>
                )}
              </div>
            );
          })
        )}

        {/* Loading / Generating Indicator */}
        {isLoading && (
          <div className="hud-msg-row msg-assistant">
            <div className="hud-msg-avatar assistant-avatar" aria-hidden="true">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle
                  cx="12"
                  cy="12"
                  r="8.5"
                  stroke="#FF3038"
                  strokeWidth="1.8"
                  strokeDasharray="36 8"
                  strokeLinecap="round"
                />
                <circle cx="12" cy="12" r="2.6" fill="#FF3038" />
              </svg>
            </div>
            <div className="hud-msg-column">
              <div className="hud-msg-card hud-loading-card">
                <div className="hud-typing-dots">
                  <span className="hud-dot" />
                  <span className="hud-dot" />
                  <span className="hud-dot" />
                </div>
              </div>
              <div className="hud-msg-timestamp">
                <Clock size={10} className="ts-clock-icon" />
                <span>
                  {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Bottom Input Capsule (Matching Reference Image) ─────────── */}
      <div className="hud-chat-footer">
        <form onSubmit={handleSubmit} className="hud-chat-input-pill">
          <input
            type="text"
            value={inputText}
            onChange={(e) => {
              setInputText(e.target.value);
              onDraftChange?.(e.target.value);
              onUserInteraction?.();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="hud-chat-text-input"
            aria-label="Type message to JARVIS"
          />
          <button
            type="submit"
            className="hud-chat-send-btn"
            disabled={!inputText.trim() || isLoading}
            aria-label="Send message"
            title="Send message"
          >
            {/* Glowing Red Send Chevron / Arrow */}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#FF3038"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="send-icon-svg"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" fill="rgba(255, 48, 56, 0.2)" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
};
