import React from 'react';
import {
  AlertTriangle,
  Mic,
  Radio,
  Square,
  Volume2,
  VolumeX,
} from 'lucide-react';
import './VoiceControls.css';

interface VoiceControlsProps {
  isVoiceActive: boolean;
  isMuted: boolean;
  hasMicPermission: boolean | null;
  audioLevel?: number; // 0 to 1
  onToggleVoice: () => void;
  onToggleMute: () => void;
  onDisconnect: () => void;
  onRequestPermission?: () => void;
}

export const VoiceControls: React.FC<VoiceControlsProps> = ({
  isVoiceActive,
  isMuted,
  hasMicPermission,
  audioLevel = 0,
  onToggleVoice,
  onToggleMute,
  onDisconnect,
  onRequestPermission,
}) => {
  // Equalizer bar heights based on audioLevel
  const barCount = 7;
  const bars = Array.from({ length: barCount }, (_, index) => {
    if (!isVoiceActive || isMuted) return 15;
    const offset = Math.sin((index / barCount) * Math.PI);
    const height = Math.max(15, Math.min(100, audioLevel * 100 * offset + Math.random() * 20));
    return Math.round(height);
  });

  return (
    <div className="voice-controls-panel">
      {/* Mic Permission Warning Banner if denied */}
      {hasMicPermission === false && (
        <div className="permission-alert">
          <AlertTriangle size={15} color="var(--rose)" />
          <span>Microphone access was denied in system settings.</span>
          {onRequestPermission && (
            <button
              type="button"
              className="permission-retry-btn"
              onClick={onRequestPermission}
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Main Controls Row */}
      <div className="controls-row">
        {/* Push to talk / Toggle voice */}
        <button
          type="button"
          className={`control-btn mic-btn ${isVoiceActive ? 'active' : ''}`}
          onClick={onToggleVoice}
          title={isVoiceActive ? 'Stop Voice Mode' : 'Start Voice Mode'}
          aria-label={isVoiceActive ? 'Stop Voice Mode' : 'Start Voice Mode'}
        >
          {isVoiceActive ? <Radio size={18} className="animate-pulse" /> : <Mic size={18} />}
          <span>{isVoiceActive ? 'Voice Active' : 'Start Voice'}</span>
        </button>

        {/* Audio Visualizer */}
        <div className={`audio-visualizer ${isVoiceActive && !isMuted ? 'active' : ''}`}>
          {bars.map((h, i) => (
            <span
              key={i}
              className="eq-bar"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>

        {/* Mute Button */}
        <button
          type="button"
          className={`control-btn icon-btn ${isMuted ? 'muted' : ''}`}
          onClick={onToggleMute}
          disabled={!isVoiceActive}
          title={isMuted ? 'Unmute Audio' : 'Mute Audio'}
          aria-label={isMuted ? 'Unmute Audio' : 'Mute Audio'}
        >
          {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
        </button>

        {/* Emergency Stop / Disconnect Button */}
        <button
          type="button"
          className="control-btn icon-btn danger-btn"
          onClick={onDisconnect}
          title="Disconnect / Emergency Stop"
          aria-label="Disconnect / Emergency Stop"
        >
          <Square size={16} fill="currentColor" />
          <span className="disconnect-label">Stop</span>
        </button>
      </div>
    </div>
  );
};

export default VoiceControls;
