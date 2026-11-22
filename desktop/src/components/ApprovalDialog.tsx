import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileCode,
  History,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  X,
  XCircle,
  Zap,
} from 'lucide-react';
import {
  approveAction,
  fetchApprovals,
  fetchAuditEvents,
  rejectAction,
  requestAction,
  type Approval,
  type AuditEvent,
} from '../lib/api';
import './ApprovalDialog.css';

interface ApprovalDialogProps {
  onApprovalsUpdated?: () => void;
}

// Generate plain-English detailed explanation of the action to be performed
export function getActionSummary(actionType: string, args: Record<string, unknown> = {}): string {
  switch (actionType) {
    case 'delete_file': {
      const path = (args.file_path as string) || 'specified file';
      return `Permanently delete file "${path}" from your local disk storage. This will unlink and permanently erase the file. This operation cannot be undone.`;
    }
    case 'open_allowed_application': {
      const app = (args.application as string) || 'application';
      return `Launch the desktop application "${app}" on your host system without shell execution.`;
    }
    case 'read_allowed_text_file': {
      const path = (args.file_path as string) || 'specified file';
      return `Read and inspect the contents of "${path}" inside the approved sandbox directory into JARVIS memory.`;
    }
    case 'search_local_memory': {
      const q = (args.query as string) || '';
      return `Search approved persistent memory records for query keyword: "${q}".`;
    }
    default:
      return `Execute tool handler "${actionType}" with validated parameter payload.`;
  }
}

export function getActionRiskLevel(actionType: string): string {
  switch (actionType) {
    case 'delete_file':
      return 'CRITICAL · IRREVERSIBLE DELETION';
    case 'open_allowed_application':
      return 'MEDIUM · APPLICATION LAUNCH';
    case 'read_allowed_text_file':
      return 'LOW · READ-ONLY FILE ACCESS';
    default:
      return 'HIGH · EXPLICIT APPROVAL REQUIRED';
  }
}

export function ApprovalDialog({ onApprovalsUpdated }: ApprovalDialogProps) {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [activeSubTab, setActiveSubTab] = useState<'pending' | 'audit'>('pending');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState<Approval | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      if (activeSubTab === 'pending') {
        const data = await fetchApprovals('pending');
        setApprovals(data.approvals);
      } else {
        const auditData = await fetchAuditEvents(50);
        setAuditEvents(auditData.events);
      }
      onApprovalsUpdated?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load approvals or audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [activeSubTab]);

  const handleApprove = async (id: string) => {
    try {
      setError(null);
      setActionSuccess(null);
      await approveAction(id);
      setActionSuccess(`Action ${id} successfully authorized and executed.`);
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Approval failed');
    }
  };

  const handleReject = async (id: string) => {
    try {
      setError(null);
      setActionSuccess(null);
      await rejectAction(id);
      setActionSuccess(`Action ${id} rejected.`);
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Rejection failed');
    }
  };

  const handleSimulateDeleteAction = async () => {
    try {
      setError(null);
      setActionSuccess(null);
      await requestAction('delete_file', {
        file_path: 'F:/Coding/docs/temporary_telemetry_cache.txt',
      });
      await loadData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Action request failed');
    }
  };

  return (
    <div className="approval-panel-container">
      {/* Header and Controls */}
      <div className="approval-header-card">
        <div className="approval-header-info">
          <h2 className="approval-title">
            <ShieldAlert size={18} color="var(--color-warning)" />
            <span>Security Approvals & Audit Trail</span>
          </h2>
          <p className="approval-subtitle">
            Approval-first policy engine preventing unauthorized file operations, shell executions, or account modifications
          </p>
        </div>

        <div className="approval-header-actions">
          <button
            type="button"
            onClick={handleSimulateDeleteAction}
            className="test-gate-btn"
            title="Queue a sample destructive action to test the approval gate"
          >
            <Zap size={14} />
            <span>Test Approval Gate</span>
          </button>
          <button
            type="button"
            onClick={loadData}
            className="refresh-icon-btn"
            title="Refresh list"
          >
            <RotateCcw size={14} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="approval-subtabs-row">
        <button
          type="button"
          onClick={() => setActiveSubTab('pending')}
          className={`subtab-btn ${activeSubTab === 'pending' ? 'active-pending' : ''}`}
        >
          <ShieldAlert size={14} />
          <span>Pending Authorizations</span>
          {approvals.length > 0 && (
            <span className="pending-counter-badge">{approvals.length}</span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab('audit')}
          className={`subtab-btn ${activeSubTab === 'audit' ? 'active-audit' : ''}`}
        >
          <History size={14} />
          <span>Audit History Trail</span>
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="alert-banner">
          <AlertTriangle size={15} color="var(--color-error)" />
          <span>{error}</span>
        </div>
      )}

      {actionSuccess && (
        <div className="alert-banner" style={{ borderColor: 'rgba(74, 222, 128, 0.3)', color: 'var(--color-success)' }}>
          <CheckCircle2 size={15} color="var(--color-success)" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Main View Area */}
      <div className="approval-list-scroll">
        {activeSubTab === 'pending' ? (
          approvals.length === 0 ? (
            <div className="approval-empty-state">
              <ShieldCheck size={36} color="var(--color-success)" />
              <p className="nominal-title">All Systems Nominal</p>
              <p className="nominal-desc">
                Zero pending actions awaiting authorization. Any destructive or consequential actions requested by JARVIS will appear here for your explicit approval.
              </p>
            </div>
          ) : (
            approvals.map((approval) => (
              <div key={approval.id} className="approval-card">
                <div className="approval-card-top">
                  <div className="action-info-group">
                    <span className="action-icon-pill">
                      <ShieldAlert size={16} />
                    </span>
                    <div>
                      <div className="action-names-row">
                        <span className="action-type-label">{approval.action_type}</span>
                        <span className="policy-badge">
                          {approval.policy.replace('_', ' ')}
                        </span>
                      </div>
                      <span className="approval-id-meta">ID: {approval.id}</span>
                    </div>
                  </div>

                  <div className="approval-expiry">
                    <Clock size={13} />
                    <span>Expires: {new Date(approval.expires_at).toLocaleTimeString()}</span>
                  </div>
                </div>

                {/* Plain-English Detailed Action Explanation */}
                <div className="action-impact-callout">
                  <div className="impact-header">
                    <AlertTriangle size={13} color="#FF3038" />
                    <span className="impact-title">Action Impact & Verification</span>
                    <span className="impact-risk-badge">{getActionRiskLevel(approval.action_type)}</span>
                  </div>
                  <p className="impact-description">
                    {getActionSummary(approval.action_type, approval.arguments)}
                  </p>
                </div>

                {/* Arguments Preview */}
                <div className="params-section">
                  <div className="params-header">
                    <FileCode size={13} color="var(--accent)" />
                    <span>Exact Action Parameters</span>
                  </div>
                  <pre className="params-code-block">
                    {JSON.stringify(approval.arguments, null, 2)}
                  </pre>
                </div>

                {/* Actions */}
                <div className="approval-card-actions">
                  <button
                    type="button"
                    onClick={() => handleReject(approval.id)}
                    className="btn-reject"
                  >
                    <XCircle size={14} color="var(--color-error)" />
                    <span>Reject Action</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setPendingConfirmation(approval)}
                    className="btn-authorize"
                  >
                    <CheckCircle2 size={14} />
                    <span>Authorize & Execute</span>
                  </button>
                </div>
              </div>
            ))
          )
        ) : (
          /* Audit History View */
          auditEvents.length === 0 ? (
            <div className="approval-empty-state">
              <History size={36} color="var(--text-tertiary)" />
              <p className="nominal-title">Audit Log Empty</p>
              <p className="nominal-desc">
                No tool executions or security decisions logged yet.
              </p>
            </div>
          ) : (
            <div className="audit-events-list">
              {auditEvents.map((event) => {
                const isSuccess = event.outcome === 'success';
                const isDenied = event.outcome === 'denied';
                const isRejected = event.outcome === 'rejected';

                return (
                  <div key={event.id} className="audit-event-card">
                    <div className="audit-event-header">
                      <div className="audit-meta-group">
                        <span className="audit-action-type">{event.action_type}</span>
                        <span
                          className={`outcome-badge ${
                            isSuccess
                              ? 'outcome-success'
                              : isDenied || isRejected
                              ? 'outcome-rejected'
                              : 'outcome-pending'
                          }`}
                        >
                          {event.outcome}
                        </span>
                      </div>

                      <span className="audit-timestamp">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>

                    <pre className="audit-details-code">
                      {JSON.stringify(event.details, null, 2)}
                    </pre>
                  </div>
                );
              })}
            </div>
          )
        )}
      </div>

      {/* Detailed Final Action Confirmation Modal */}
      {pendingConfirmation && (
        <div
          className="confirmation-modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-action-title"
        >
          <div className="confirmation-modal-card">
            <div className="modal-header">
              <div className="modal-title-group">
                <ShieldAlert size={20} color="#FF3038" />
                <div>
                  <h3 id="modal-action-title" className="modal-title">
                    FINAL ACTION CONFIRMATION
                  </h3>
                  <span className="modal-subtitle">
                    Security Policy Engine · Explicit Authorization Required
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setPendingConfirmation(null)}
                aria-label="Close confirmation dialog"
              >
                <X size={16} />
              </button>
            </div>

            <div className="modal-body">
              <div className="modal-warning-box">
                <AlertTriangle size={20} color="#FF3038" className="modal-warning-icon" />
                <div className="modal-warning-text">
                  <span className="warning-heading">Action to be performed:</span>
                  <p className="warning-detail">
                    {getActionSummary(pendingConfirmation.action_type, pendingConfirmation.arguments)}
                  </p>
                </div>
              </div>

              <div className="modal-meta-grid">
                <div className="modal-meta-item">
                  <span className="meta-label">Action Handler</span>
                  <span className="meta-val font-mono">{pendingConfirmation.action_type}</span>
                </div>
                <div className="modal-meta-item">
                  <span className="meta-label">Risk Assessment</span>
                  <span className="meta-val font-mono risk-highlight">
                    {getActionRiskLevel(pendingConfirmation.action_type)}
                  </span>
                </div>
                <div className="modal-meta-item">
                  <span className="meta-label">Approval ID</span>
                  <span className="meta-val font-mono">{pendingConfirmation.id}</span>
                </div>
                <div className="modal-meta-item">
                  <span className="meta-label">Security Policy</span>
                  <span className="meta-val font-mono">
                    {pendingConfirmation.policy.replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div className="modal-params-box">
                <span className="modal-params-label">Exact Parameters:</span>
                <pre className="modal-params-code">
                  {JSON.stringify(pendingConfirmation.arguments, null, 2)}
                </pre>
              </div>
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="btn-modal-cancel"
                onClick={() => setPendingConfirmation(null)}
              >
                Cancel / Abort
              </button>
              <button
                type="button"
                className="btn-modal-confirm"
                onClick={() => {
                  const id = pendingConfirmation.id;
                  setPendingConfirmation(null);
                  handleApprove(id);
                }}
              >
                <CheckCircle2 size={15} />
                <span>Confirm & Execute Now</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ApprovalDialog;
