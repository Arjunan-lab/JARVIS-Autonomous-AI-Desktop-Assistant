import React, { useEffect, useState } from 'react';

interface TypewriterTextProps {
  text: string;
  isNew?: boolean;
  charIntervalMs?: number;
  onCharacterTyped?: () => void;
  onComplete?: () => void;
}

export const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  isNew = false,
  charIntervalMs = 45,
  onCharacterTyped,
  onComplete,
}) => {
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;

  // If not new or user prefers reduced motion, render complete text immediately
  const [displayedLength, setDisplayedLength] = useState<number>(() => {
    if (!isNew || prefersReducedMotion) return text.length;
    return 1;
  });

  const isComplete = displayedLength >= text.length;

  useEffect(() => {
    if (!isNew || prefersReducedMotion) {
      onComplete?.();
      return;
    }

    if (isComplete) {
      onComplete?.();
      return;
    }

    const prevChar = text[displayedLength - 1];
    let delay = charIntervalMs;

    // Natural cinematic pauses after punctuation
    if (prevChar === ',' || prevChar === ';') {
      delay += 90;
    } else if (prevChar === '.' || prevChar === '!' || prevChar === '?') {
      delay += 180;
    } else if (prevChar === '\n') {
      delay += 240;
    }

    const timer = setTimeout(() => {
      setDisplayedLength((prev) => prev + 1);
      onCharacterTyped?.();
    }, delay);

    return () => clearTimeout(timer);
  }, [displayedLength, text, isNew, charIntervalMs, prefersReducedMotion, isComplete, onCharacterTyped, onComplete]);

  if (!isNew || prefersReducedMotion) {
    return <span className="typewriter-content">{text}</span>;
  }

  return (
    <span className="typewriter-content">
      {text.slice(0, displayedLength)}
      {!isComplete && <span className="typewriter-cursor" aria-hidden="true" />}
    </span>
  );
};
