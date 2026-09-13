import React from 'react';
import { Bell, AlertTriangle, ShieldAlert } from 'lucide-react';
import { Alert } from '../../types/api';

interface RecentAlertsProps {
  alerts: Alert[];
  isLoading?: boolean;
  error?: string | null;
}

export const RecentAlerts: React.FC<RecentAlertsProps> = ({ alerts = [], isLoading, error }) => {
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  const getBadgeClass = (level?: string) => {
    return level === 'HIGH RISK' ? 'risk-pill high-risk' : 'risk-pill suspicious';
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <Bell size={16} /> Recent Risk Alerts ({safeAlerts.length})
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          LEVEL-ESCALATION FILTER ACTIVE
        </span>
      </div>

      <div className="panel-body" style={{ overflowY: 'auto', maxHeight: '300px' }}>
        {isLoading ? (
          <div className="empty-state">
            <div style={{ color: 'var(--accent-cyan)' }}>Loading risk alerts...</div>
          </div>
        ) : error ? (
          <div className="empty-state">
            <AlertTriangle size={28} style={{ color: 'var(--color-high-risk)' }} />
            <div className="empty-state-text" style={{ color: 'var(--color-high-risk)' }}>Alert Feed Unavailable</div>
            <div className="empty-state-sub">{error}</div>
          </div>
        ) : safeAlerts.length === 0 ? (
          <div className="empty-state">
            <ShieldAlert size={28} />
            <div className="empty-state-text">No Risk Escalation Alerts</div>
            <div className="empty-state-sub">Zero target risk level escalations recorded in sequence.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {safeAlerts.map((alert, idx) => {
              const alertLevel = alert?.level || 'SUSPICIOUS';
              const targetId = alert?.target_id ?? idx;
              const alertScore = alert?.score ?? 0;
              const alertMsg = alert?.message || 'Geofence intrusion / risk indicator';
              const alertReasons = alert?.reasons || [];

              return (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    borderLeft: `4px solid ${alertLevel === 'HIGH RISK' ? 'var(--color-high-risk)' : 'var(--color-suspicious)'}`,
                    borderTop: '1px solid var(--border-subtle)',
                    borderRight: '1px solid var(--border-subtle)',
                    borderBottom: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '0.65rem 0.75rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                      Target #{targetId} Risk Alert
                    </div>
                    <span className={getBadgeClass(alertLevel)}>
                      {alertLevel} (Score: {alertScore})
                    </span>
                  </div>

                  <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    {alertMsg}
                  </div>

                  {alertReasons.length > 0 && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {alertReasons.map((reason, rIdx) => (
                        <div key={rIdx}>• {reason}</div>
                      ))}
                    </div>
                  )}

                  <div style={{ fontSize: '0.68rem', color: 'var(--color-monitor)', fontStyle: 'italic', marginTop: '2px' }}>
                    • Human verification required
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default RecentAlerts;

