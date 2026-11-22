import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  FolderLock,
  RotateCcw,
  Shield,
  Sliders,
  Sparkles,
} from 'lucide-react';
import {
  fetchBudgetStatus,
  fetchSettings,
  resetDailyBudget,
  updateSettings,
  type AppSettings,
  type BudgetStatus,
} from '../lib/api';
import './SettingsPanel.css';

export function SettingsPanel() {
  const [budget, setBudget] = useState<BudgetStatus | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [newLimit, setNewLimit] = useState<string>('1.00');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [budgetData, settingsData] = await Promise.all([
        fetchBudgetStatus(),
        fetchSettings(),
      ]);
      setBudget(budgetData);
      setSettings(settingsData);
      setNewLimit(budgetData.limit_usd.toFixed(2));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load settings or budget data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleUpdateLimit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseFloat(newLimit);
    if (isNaN(parsed) || parsed <= 0) {
      setError('Please enter a valid positive dollar amount.');
      return;
    }

    try {
      setError(null);
      setSuccessMsg(null);
      await updateSettings({ max_daily_budget_usd: parsed });
      setSuccessMsg(`Daily API budget limit updated to $${parsed.toFixed(2)} USD.`);
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update budget limit');
    }
  };

  const handleResetBudget = async () => {
    try {
      setError(null);
      setSuccessMsg(null);
      await resetDailyBudget();
      setSuccessMsg('Daily API spend counter has been reset to $0.00.');
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to reset daily budget');
    }
  };

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const remainingSec = sec % 60;
    return `${mins}m ${remainingSec}s`;
  };

  const percentSpent = budget
    ? Math.min(100, Math.round((budget.spent_usd / budget.limit_usd) * 100))
    : 0;

  return (
    <div className="settings-panel-container">
      {/* Header */}
      <div className="settings-header-card">
        <div className="settings-header-info">
          <h2 className="settings-title">
            <Sliders size={18} color="var(--accent)" />
            <span>System Settings & Budget Safeguards</span>
          </h2>
          <p className="settings-subtitle">
            Realtime API spending caps, session duration limits, voice models, and sandboxed directories
          </p>
        </div>

        <button
          type="button"
          onClick={loadData}
          className="settings-refresh-btn"
          title="Refresh metrics"
        >
          <RotateCcw size={14} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="alert-banner">
          <AlertTriangle size={15} color="var(--color-error)" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="alert-banner" style={{ borderColor: 'rgba(74, 222, 128, 0.3)', color: 'var(--color-success)' }}>
          <CheckCircle2 size={15} color="var(--color-success)" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Grid of Settings Cards */}
      <div className="settings-cards-grid">
        {/* Card 1: API Budget Safeguard */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="card-title-group">
              <DollarSign size={16} color="var(--color-success)" />
              <span>Daily API Budget Safeguard</span>
            </div>
            <span
              className={`status-badge ${
                budget?.is_budget_exceeded ? 'exceeded' : 'protected'
              }`}
            >
              {budget?.is_budget_exceeded ? 'Cap Exceeded' : 'Protected'}
            </span>
          </div>

          {/* Progress bar */}
          <div className="budget-progress-section">
            <div className="progress-labels-row">
              <span className="progress-label-dim">Today's Estimated Spend</span>
              <span className="progress-label-val">
                ${(budget?.spent_usd ?? 0).toFixed(2)} / ${(budget?.limit_usd ?? 5).toFixed(2)} USD
              </span>
            </div>

            <div className="progress-track">
              <div
                className={`progress-bar-fill ${
                  percentSpent >= 100
                    ? 'danger'
                    : percentSpent >= 80
                    ? 'warning'
                    : 'safe'
                }`}
                style={{ width: `${percentSpent}%` }}
              />
            </div>

            <div className="progress-meta-row">
              <span>{percentSpent}% consumed</span>
              <span>Remaining: ${(budget?.remaining_usd ?? 5).toFixed(2)}</span>
            </div>
          </div>

          {/* Telemetry metrics */}
          <div className="telemetry-grid">
            <div className="telemetry-tile">
              <span className="telemetry-title">Sessions Today</span>
              <span className="telemetry-val">{budget?.sessions_today ?? 0}</span>
            </div>
            <div className="telemetry-tile">
              <span className="telemetry-title">Total Voice Duration</span>
              <span className="telemetry-val" style={{ color: 'var(--accent)' }}>
                {formatSeconds(budget?.duration_seconds_today ?? 0)}
              </span>
            </div>
          </div>

          {/* Limit Form */}
          <form onSubmit={handleUpdateLimit} className="budget-form">
            <div className="input-prefix-wrapper">
              <span className="input-prefix">$</span>
              <input
                type="number"
                step="0.25"
                min="0.25"
                max="50.00"
                value={newLimit}
                onChange={(e) => setNewLimit(e.target.value)}
                className="budget-input"
              />
            </div>
            <button type="submit" className="btn-update-limit">
              Update Limit
            </button>
            <button
              type="button"
              onClick={handleResetBudget}
              className="btn-reset-limit"
              title="Reset today's usage counter"
            >
              Reset
            </button>
          </form>
        </div>

        {/* Card 2: Voice Model & Persona */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="card-title-group">
              <Cpu size={16} color="var(--accent)" />
              <span>Voice Engine Configuration</span>
            </div>
            <span className="status-badge info">
              {settings?.ai_provider === 'gemini' ? 'Gemini Live' : 'WebRTC Direct'}
            </span>
          </div>

          <div className="config-kv-list">
            <div className="config-kv-item">
              <span className="kv-key">AI Engine Provider</span>
              <span className="kv-val accent">
                {settings?.ai_provider === 'gemini' ? 'Google Gemini' : 'OpenAI'}
              </span>
            </div>

            <div className="config-kv-item">
              <span className="kv-key">Reasoning Model</span>
              <span className="kv-val">
                {settings?.ai_provider === 'gemini'
                  ? (settings?.gemini_model ?? 'gemini-2.0-flash')
                  : (settings?.openai_model ?? 'gpt-realtime-mini')}
              </span>
            </div>

            <div className="config-kv-item">
              <span className="kv-key">Voice Persona</span>
              <span className="kv-val accent">
                {settings?.ai_provider === 'gemini'
                  ? (settings?.gemini_voice ?? 'Puck')
                  : (settings?.openai_voice ?? 'marin')}
              </span>
            </div>

            <div className="config-kv-item">
              <span className="kv-key">API Key Isolation</span>
              <span className="kv-val success">
                <CheckCircle2 size={13} />
                <span>Server-Side Only</span>
              </span>
            </div>

            <div className="config-kv-item">
              <span className="kv-key">Audio Transport</span>
              <span className="kv-val" style={{ color: 'var(--text-secondary)' }}>
                {settings?.ai_provider === 'gemini' ? 'WebSocket PCM Bridge' : 'WebRTC PCM 24kHz'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Sandboxed Directories */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="card-title-group">
              <FolderLock size={16} color="#60A5FA" />
              <span>Authorized File System Folders</span>
            </div>
            <span className="status-badge sandboxed">
              Sandboxed
            </span>
          </div>

          <p className="sandbox-desc">
            Local file operations and keyword document searches are strictly confined to these folders. Directory escape and path traversal outside these roots is blocked by the security policy engine.
          </p>

          <div className="sandbox-dirs-list">
            {settings?.allowed_dirs && settings.allowed_dirs.length > 0 ? (
              settings.allowed_dirs.map((dir, idx) => (
                <div key={idx} className="sandbox-dir-item" title={dir}>
                  {dir}
                </div>
              ))
            ) : (
              <div className="sandbox-dir-item" style={{ color: 'var(--text-tertiary)', fontStyle: 'italic' }}>
                No custom folders configured. Set JARVIS_ALLOWED_DIRS in backend/.env
              </div>
            )}
          </div>
        </div>

        {/* Card 4: Error Recovery & Resilience */}
        <div className="settings-card">
          <div className="settings-card-header">
            <div className="card-title-group">
              <Shield size={16} color="var(--accent)" />
              <span>Resilience & Reconnect Engine</span>
            </div>
            <span className="status-badge info">
              Active
            </span>
          </div>

          <div className="resilience-checklist">
            <div className="checklist-item">
              <Sparkles size={14} color="var(--accent)" />
              <span>Bounded exponential reconnect (max 3 retries)</span>
            </div>
            <div className="checklist-item">
              <Clock size={14} color="var(--accent)" />
              <span>Session duration limit (10 min safeguard timeout)</span>
            </div>
            <div className="checklist-item">
              <CheckCircle2 size={14} color="var(--accent)" />
              <span>Zero client credential leaks (ephemeral ek_ tokens only)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default SettingsPanel;
