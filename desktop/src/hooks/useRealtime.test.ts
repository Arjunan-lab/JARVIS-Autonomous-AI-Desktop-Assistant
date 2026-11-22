import { act, renderHook } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useRealtime } from './useRealtime';
import * as realtimeLib from '../lib/realtime';

vi.mock('../lib/realtime', () => ({
  fetchVoiceSession: vi.fn(),
  createRealtimePeerConnection: vi.fn(),
}));

describe('useRealtime Hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('initializes with default disconnected and idle states', () => {
    const { result } = renderHook(() => useRealtime());

    expect(result.current.connectionStatus).toBe('disconnected');
    expect(result.current.orbState).toBe('idle');
    expect(result.current.isMuted).toBe(false);
    expect(result.current.audioLevel).toBe(0);
    expect(result.current.errorMessage).toBeNull();
  });

  it('starts voice session and handles connected state', async () => {
    const mockSession = {
      client_secret: 'ek_test_secret',
      expires_at: 1800000000,
      session_id: 'sess_123',
      model: 'gpt-realtime-mini',
      voice: 'marin',
    };

    const mockTrack = { stop: vi.fn(), enabled: true };
    const mockStream = {
      getTracks: () => [mockTrack],
      getAudioTracks: () => [mockTrack],
    };
    const mockDc = { close: vi.fn(), readyState: 'open', send: vi.fn() };
    const mockPc = { close: vi.fn(), connectionState: 'connected' };
    const mockAudioEl = { srcObject: null };

    vi.mocked(realtimeLib.fetchVoiceSession).mockResolvedValueOnce(mockSession);
    vi.mocked(realtimeLib.createRealtimePeerConnection).mockResolvedValueOnce({
      pc: mockPc as unknown as RTCPeerConnection,
      dc: mockDc as unknown as RTCDataChannel,
      localStream: mockStream as unknown as MediaStream,
      audioEl: mockAudioEl as unknown as HTMLAudioElement,
    });

    const { result } = renderHook(() => useRealtime());

    await act(async () => {
      await result.current.startSession();
    });

    expect(result.current.connectionStatus).toBe('connected');
    expect(result.current.orbState).toBe('listening');
    expect(result.current.sessionData?.session_id).toBe('sess_123');
  });

  it('handles session errors gracefully', async () => {
    vi.mocked(realtimeLib.fetchVoiceSession).mockRejectedValueOnce(
      new Error('Backend rejected session: missing OpenAI API key')
    );

    const { result } = renderHook(() => useRealtime());

    await act(async () => {
      await result.current.startSession();
    });

    expect(result.current.connectionStatus).toBe('error');
    expect(result.current.orbState).toBe('error');
    expect(result.current.errorMessage).toContain('missing OpenAI API key');
  });

  it('disconnects and releases resources properly', async () => {
    const mockTrack = { stop: vi.fn(), enabled: true };
    const mockStream = {
      getTracks: () => [mockTrack],
      getAudioTracks: () => [mockTrack],
    };
    const mockDc = { close: vi.fn(), readyState: 'open', send: vi.fn() };
    const mockPc = { close: vi.fn() };
    const mockAudioEl = { srcObject: null };

    vi.mocked(realtimeLib.fetchVoiceSession).mockResolvedValueOnce({
      client_secret: 'ek_123',
      expires_at: 1800000000,
      session_id: 'sess_1',
      model: 'gpt-realtime-mini',
      voice: 'marin',
    });
    vi.mocked(realtimeLib.createRealtimePeerConnection).mockResolvedValueOnce({
      pc: mockPc as unknown as RTCPeerConnection,
      dc: mockDc as unknown as RTCDataChannel,
      localStream: mockStream as unknown as MediaStream,
      audioEl: mockAudioEl as unknown as HTMLAudioElement,
    });

    const { result } = renderHook(() => useRealtime());

    await act(async () => {
      await result.current.startSession();
    });

    act(() => {
      result.current.disconnectSession();
    });

    expect(result.current.connectionStatus).toBe('disconnected');
    expect(result.current.orbState).toBe('idle');
    expect(mockTrack.stop).toHaveBeenCalled();
    expect(mockPc.close).toHaveBeenCalled();
  });
});
