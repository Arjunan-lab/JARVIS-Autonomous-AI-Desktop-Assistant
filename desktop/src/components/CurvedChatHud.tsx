import React, { useEffect, useRef, useState } from 'react';
import './CurvedChatHud.css';

export interface ChatHudMessage {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  timestamp?: string;
}

interface CurvedChatHudProps {
  message: ChatHudMessage | null;
  onVanish?: () => void;
  vanishDelayMs?: number; // Default 5000ms
}

export const CurvedChatHud: React.FC<CurvedChatHudProps> = ({
  message,
  onVanish,
  vanishDelayMs = 5000,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [visible, setVisible] = useState(false);

  const typewriterTimerRef = useRef<number | null>(null);
  const vanishTimerRef = useRef<number | null>(null);
  const fadeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!message || !message.text) {
      setVisible(false);
      return;
    }

    // Reset all previous timers on new message
    if (typewriterTimerRef.current) clearInterval(typewriterTimerRef.current);
    if (vanishTimerRef.current) clearTimeout(vanishTimerRef.current);
    if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);

    setVisible(true);
    setIsFadingOut(false);
    setDisplayedText('');
    setIsTyping(true);

    const fullText = message.text;
    let charIndex = 0;

    // Typewriting animation: 18ms per character
    typewriterTimerRef.current = window.setInterval(() => {
      charIndex++;
      setDisplayedText(fullText.slice(0, charIndex));

      if (charIndex >= fullText.length) {
        if (typewriterTimerRef.current) {
          clearInterval(typewriterTimerRef.current);
          typewriterTimerRef.current = null;
        }
        setIsTyping(false);

        // 5-second countdown to vanish
        vanishTimerRef.current = window.setTimeout(() => {
          setIsFadingOut(true);

          // Allow 800ms for smooth fade/blur transition before unmounting
          fadeTimerRef.current = window.setTimeout(() => {
            setVisible(false);
            onVanish?.();
          }, 800);
        }, vanishDelayMs);
      }
    }, 18);

    return () => {
      if (typewriterTimerRef.current) clearInterval(typewriterTimerRef.current);
      if (vanishTimerRef.current) clearTimeout(vanishTimerRef.current);
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current);
    };
  }, [message, vanishDelayMs, onVanish]);

  if (!visible || !message) return null;

  const isUser = message.sender === 'user';

  return (
    <div
      className={`curved-hud-overlay ${isFadingOut ? 'fade-out' : 'fade-in'}`}
      role="region"
      aria-label="JARVIS Holographic HUD Chat"
    >
      <div className="curved-hud-container">
        {/* Top Holographic Curved Arc Line */}
        <div className="hud-arc-top">
          <svg
            className="hud-curve-svg"
            viewBox="0 0 640 40"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            {/* Gentle curved hairline arch */}
            <path
              d="M 20,32 Q 320,4 620,32"
              stroke="#FF3038"
              strokeWidth="1"
              strokeOpacity="0.45"
              fill="none"
            />
            {/* Cardinal end ticks */}
            <line x1="20" y1="28" x2="20" y2="36" stroke="#FF3038" strokeWidth="1.5" strokeOpacity="0.75" />
            <line x1="620" y1="28" x2="620" y2="36" stroke="#FF3038" strokeWidth="1.5" strokeOpacity="0.75" />
            {/* Center radiant neural dot */}
            <circle cx="320" cy="18" r="2" fill="#FF3038" />
            <circle cx="320" cy="18" r="4.5" stroke="#FF3038" strokeWidth="0.75" strokeOpacity="0.5" />
          </svg>
        </div>

        {/* Floating Typography (Zero Background) */}
        <div className={`hud-message-content ${isUser ? 'sender-user' : 'sender-jarvis'}`}>
          <div className="hud-sender-tag">
            <span className="sender-indicator-dot" />
            <span className="sender-name">
              {isUser ? 'USER · VOCAL INPUT' : 'JARVIS · NEURAL SYNTHESIS'}
            </span>
            <span className="hud-session-mark">HUD // ACTIVE</span>
          </div>

          <div className="hud-text-body">
            <span className="hud-typewritten-text">{displayedText}</span>
            {isTyping && <span className="hud-cursor-pulse" aria-hidden="true">▎</span>}
          </div>
        </div>

        {/* Bottom Holographic Curved Arc Line */}
        <div className="hud-arc-bottom">
          <svg
            className="hud-curve-svg"
            viewBox="0 0 640 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            {/* Inverted gentle curved hairline arch */}
            <path
              d="M 60,8 Q 320,30 580,8"
              stroke="#FF3038"
              strokeWidth="0.85"
              strokeOpacity="0.35"
              fill="none"
            />
            {/* Flanking accent tick dots */}
            <circle cx="280" cy="24" r="1.2" fill="#FF3038" fillOpacity="0.6" />
            <circle cx="360" cy="24" r="1.2" fill="#FF3038" fillOpacity="0.6" />
          </svg>
        </div>
      </div>
    </div>
  );
};

export default CurvedChatHud;
