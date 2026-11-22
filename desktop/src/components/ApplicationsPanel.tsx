import React, { useEffect, useId, useState } from 'react';
import {
  AlertCircle,
  AppWindow,
  CheckCircle2,
  Code,
  FileText,
  Film,
  Gamepad2,
  Globe,
  Play,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Wrench,
  X,
} from 'lucide-react';
import {
  fetchApplications,
  launchApplication,
  type ManagedApp,
  refreshApplications,
  updateAppPermission,
} from '../lib/api';
import './ApplicationsPanel.css';

interface ApplicationsPanelProps {
  onStatusMessage?: (msg: string) => void;
}

export const ApplicationsPanel: React.FC<ApplicationsPanelProps> = ({ onStatusMessage }) => {
  const searchInputId = useId();
  const [apps, setApps] = useState<ManagedApp[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [enabledCount, setEnabledCount] = useState<number>(0);
  const [disabledCount, setDisabledCount] = useState<number>(0);
  const [categories, setCategories] = useState<string[]>([]);

  // Filter States
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [enabledOnly, setEnabledOnly] = useState<boolean>(false);

  // Status & Loading States
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [launchingAppId, setLaunchingAppId] = useState<string | null>(null);
  const [updatingAppId, setUpdatingAppId] = useState<string | null>(null);

  const loadApps = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchApplications({
        search: searchQuery.trim() || undefined,
        category: selectedCategory === 'All' ? undefined : selectedCategory,
        enabled_only: enabledOnly,
      });
      setApps(res.applications);
      setTotalCount(res.total_count);
      setEnabledCount(res.enabled_count);
      setDisabledCount(res.disabled_count);
      setCategories(res.categories);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load application catalog');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadApps();
  }, [searchQuery, selectedCategory, enabledOnly]);

  const handleRefreshDiscovery = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const res = await refreshApplications();
      setApps(res.applications);
      setTotalCount(res.total_count);
      setEnabledCount(res.enabled_count);
      setDisabledCount(res.disabled_count);
      setCategories(res.categories);
      setNotice({
        text: `Discovery complete: catalog synchronized with ${res.total_count} applications.`,
        type: 'success',
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Discovery refresh failed';
      setError(msg);
      setNotice({ text: msg, type: 'error' });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleTogglePermission = async (app: ManagedApp) => {
    setUpdatingAppId(app.id);
    const newStatus = !app.is_enabled;
    try {
      const updated = await updateAppPermission(app.id, newStatus);
      setApps((prev) => prev.map((a) => (a.id === app.id ? updated : a)));

      // Update aggregate metrics locally
      if (newStatus) {
        setEnabledCount((c) => c + 1);
        setDisabledCount((c) => Math.max(0, c - 1));
      } else {
        setEnabledCount((c) => Math.max(0, c - 1));
        setDisabledCount((c) => c + 1);
      }

      const statusWord = newStatus ? 'enabled' : 'disabled';
      setNotice({
        text: `Application '${app.name}' ${statusWord}.`,
        type: 'success',
      });
      if (onStatusMessage) {
        onStatusMessage(`Application '${app.name}' ${statusWord}.`);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to update application permission';
      setNotice({ text: msg, type: 'error' });
    } finally {
      setUpdatingAppId(null);
    }
  };

  const handleLaunch = async (app: ManagedApp) => {
    if (!app.is_enabled) {
      setNotice({
        text: `Launch blocked: '${app.name}' is disabled. Enable permission first.`,
        type: 'error',
      });
      return;
    }

    if (!app.is_available) {
      setNotice({
        text: `Launch failed: '${app.name}' is unavailable on this system.`,
        type: 'error',
      });
      return;
    }

    setLaunchingAppId(app.id);
    try {
      const res = await launchApplication(app.id);
      const modeText = res.mode === 'simulated' ? ' (simulated test environment)' : '';
      setNotice({
        text: `Launched '${app.name}' successfully${modeText}.`,
        type: 'success',
      });
      if (onStatusMessage) {
        onStatusMessage(`Launched '${app.name}'.`);
      }
      // Update last launched locally
      setApps((prev) =>
        prev.map((a) => (a.id === app.id ? { ...a, last_launched_at: new Date().toISOString() } : a))
      );
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Launch execution failed';
      setNotice({ text: msg, type: 'error' });
    } finally {
      setLaunchingAppId(null);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'browsers':
        return <Globe size={18} />;
      case 'development':
        return <Code size={18} />;
      case 'productivity':
        return <FileText size={18} />;
      case 'media':
        return <Film size={18} />;
      case 'games':
        return <Gamepad2 size={18} />;
      case 'utilities':
        return <Wrench size={18} />;
      default:
        return <AppWindow size={18} />;
    }
  };

  return (
    <div className="apps-panel-container">
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="apps-panel-header">
        <div className="apps-header-left">
          <div className="apps-title-row">
            <Shield size={18} className="neural-accent-icon" />
            <h3 className="apps-heading">Personal App Access Manager</h3>
          </div>
          <p className="apps-subheading">
            Controlled Windows execution boundary. Every launch is verified server-side against
            authorized permissions and validated targets. Newly discovered apps default to disabled.
          </p>
        </div>

        <div className="apps-header-actions">
          <button
            type="button"
            className="apps-refresh-btn"
            onClick={handleRefreshDiscovery}
            disabled={isRefreshing || isLoading}
            aria-label="Refresh Application Discovery"
            title="Scan authorized Windows locations to discover new apps"
          >
            <RefreshCw size={14} className={isRefreshing ? 'spinning' : ''} />
            <span>{isRefreshing ? 'Scanning…' : 'Refresh Discovery'}</span>
          </button>
        </div>
      </div>

      {/* ── Summary Metrics Bar ─────────────────────────────────── */}
      <div className="apps-metrics-grid">
        <div className="apps-metric-card">
          <span className="metric-label">Total Discovered</span>
          <div className="metric-value-row">
            <span className="metric-value">{totalCount}</span>
            <span className="metric-sub">catalog entries</span>
          </div>
        </div>

        <div className="apps-metric-card success">
          <span className="metric-label">Authorized (Enabled)</span>
          <div className="metric-value-row">
            <span className="metric-value">{enabledCount}</span>
            <span className="metric-sub">permitted to launch</span>
          </div>
        </div>

        <div className="apps-metric-card accent">
          <span className="metric-label">Blocked (Default Deny)</span>
          <div className="metric-value-row">
            <span className="metric-value">{disabledCount}</span>
            <span className="metric-sub">restricted</span>
          </div>
        </div>

        <div className="apps-metric-card">
          <span className="metric-label">Categories</span>
          <div className="metric-value-row">
            <span className="metric-value">{categories.length}</span>
            <span className="metric-sub">detected</span>
          </div>
        </div>
      </div>

      {/* ── Filtering & Search Controls ─────────────────────────── */}
      <div className="apps-controls-card">
        <div className="apps-search-row">
          <label htmlFor={searchInputId} className="apps-search-box">
            <Search size={15} />
            <input
              id={searchInputId}
              type="text"
              placeholder="Search applications by name or path…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="apps-search-input"
              aria-label="Search applications"
            />
            {searchQuery && (
              <button
                type="button"
                className="apps-search-clear"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </label>

          <button
            type="button"
            className={`apps-filter-toggle ${enabledOnly ? 'active' : ''}`}
            onClick={() => setEnabledOnly((prev) => !prev)}
            aria-pressed={enabledOnly}
            aria-label="Toggle authorized only filter"
          >
            {enabledOnly ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
            <span>{enabledOnly ? 'Authorized Only' : 'Show All'}</span>
          </button>
        </div>

        {/* Category Pills */}
        <div className="apps-category-pills" role="radiogroup" aria-label="Category filter">
          <button
            type="button"
            className={`category-pill ${selectedCategory === 'All' ? 'active' : ''}`}
            onClick={() => setSelectedCategory('All')}
            aria-checked={selectedCategory === 'All'}
            role="radio"
          >
            All ({totalCount})
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              type="button"
              className={`category-pill ${selectedCategory === cat ? 'active' : ''}`}
              onClick={() => setSelectedCategory(cat)}
              aria-checked={selectedCategory === cat}
              role="radio"
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* ── Notification Banner ─────────────────────────────────── */}
      {notice && (
        <div className={`apps-notice-banner ${notice.type}`} role="status">
          <div className="notice-content">
            {notice.type === 'success' ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
            <span>{notice.text}</span>
          </div>
          <button
            type="button"
            className="notice-dismiss"
            onClick={() => setNotice(null)}
            aria-label="Dismiss message"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* ── Error State ─────────────────────────────────────────── */}
      {error && !notice && (
        <div className="apps-state-card">
          <AlertCircle size={28} className="state-icon text-error" />
          <div className="state-title">Application Registry Error</div>
          <p className="state-desc">{error}</p>
          <button type="button" className="state-action-btn" onClick={loadApps}>
            Retry Request
          </button>
        </div>
      )}

      {/* ── Loading State ───────────────────────────────────────── */}
      {isLoading && apps.length === 0 && (
        <div className="apps-state-card">
          <RefreshCw size={28} className="state-icon spinning" />
          <div className="state-title">Accessing Windows Application Catalog</div>
          <p className="state-desc">Validating targets and synchronizing permission boundaries…</p>
        </div>
      )}

      {/* ── Empty State ─────────────────────────────────────────── */}
      {!isLoading && !error && apps.length === 0 && (
        <div className="apps-state-card">
          <ShieldAlert size={32} className="state-icon" />
          <div className="state-title">No Applications Found</div>
          <p className="state-desc">
            {searchQuery || selectedCategory !== 'All' || enabledOnly
              ? 'No applications match your active search and filter criteria.'
              : 'Click "Refresh Discovery" above to scan authorized Windows Start Menu shortcuts and registered app entries.'}
          </p>
          {searchQuery && (
            <button
              type="button"
              className="state-action-btn"
              onClick={() => {
                setSearchQuery('');
                setSelectedCategory('All');
                setEnabledOnly(false);
              }}
            >
              Reset Filters
            </button>
          )}
        </div>
      )}

      {/* ── Applications Cards Grid ─────────────────────────────── */}
      {!isLoading && apps.length > 0 && (
        <div className="apps-grid" aria-label="Applications list">
          {apps.map((app) => (
            <div
              key={app.id}
              className={`app-card ${app.is_enabled ? 'enabled' : 'disabled'} ${
                !app.is_available ? 'unavailable' : ''
              }`}
              data-testid={`app-card-${app.id}`}
            >
              <div className="app-card-top">
                <div className="app-icon-box" title={app.category}>
                  {getCategoryIcon(app.category)}
                </div>

                <div className="app-info">
                  <div className="app-name-row">
                    <span className="app-name" title={app.name}>
                      {app.name}
                    </span>
                  </div>

                  <div className="app-badges-row">
                    <span className="badge badge-category">{app.category}</span>
                    <span className="badge badge-type">{app.target_type}</span>
                    <span
                      className={`badge badge-status ${
                        app.is_available ? 'available' : 'unavailable'
                      }`}
                      title={app.is_available ? 'Available on disk' : 'Target missing or uninstalled'}
                    >
                      <span className={`status-dot ${app.is_available ? 'green' : 'amber'}`} />
                      {app.is_available ? 'Available' : 'Missing'}
                    </span>
                  </div>

                  <div className="app-target-path" title={app.target_path}>
                    {app.target_path}
                  </div>
                </div>
              </div>

              {/* Bottom Controls Row: Toggle Permission + Direct Launch */}
              <div className="app-card-bottom">
                <div className="permission-toggle-wrapper">
                  <button
                    type="button"
                    role="switch"
                    aria-checked={app.is_enabled}
                    aria-label={`Toggle permission for ${app.name}`}
                    className={`toggle-switch-btn ${app.is_enabled ? 'on' : 'off'}`}
                    onClick={() => handleTogglePermission(app)}
                    disabled={updatingAppId === app.id}
                  >
                    <span className="toggle-thumb" />
                  </button>
                  <span className={`toggle-label ${app.is_enabled ? 'on' : 'off'}`}>
                    {app.is_enabled ? 'Authorized' : 'Blocked'}
                  </span>
                </div>

                <button
                  type="button"
                  className="app-launch-btn"
                  onClick={() => handleLaunch(app)}
                  disabled={
                    !app.is_enabled ||
                    !app.is_available ||
                    launchingAppId === app.id ||
                    updatingAppId === app.id
                  }
                  aria-label={`Launch ${app.name}`}
                  title={
                    !app.is_enabled
                      ? 'Enable permission to allow launch'
                      : !app.is_available
                      ? 'Target is unavailable'
                      : `Launch ${app.name}`
                  }
                >
                  <Play size={12} />
                  <span>{launchingAppId === app.id ? 'Launching…' : 'Launch'}</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
