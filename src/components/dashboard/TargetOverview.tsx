import React from 'react';
import { Users, AlertCircle, Compass, MapPin } from 'lucide-react';
import { TargetState } from '../../types/api';

interface TargetOverviewProps {
  targets: TargetState[];
  isLoading?: boolean;
  error?: string | null;
}

export const TargetOverview: React.FC<TargetOverviewProps> = ({ targets = [], isLoading, error }) => {
  const safeTargets = Array.isArray(targets) ? targets : [];

  const getRiskBadgeClass = (level?: string) => {
    switch (level) {
      case 'NORMAL':
        return 'risk-pill normal';
      case 'MONITOR':
        return 'risk-pill monitor';
      case 'SUSPICIOUS':
        return 'risk-pill suspicious';
      case 'HIGH RISK':
        return 'risk-pill high-risk';
      default:
        return 'risk-pill normal';
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <Users size={16} /> Tracked Targets ({safeTargets.length})
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          BYTE-TRACK MOT
        </span>
      </div>

      <div className="panel-body" style={{ overflowY: 'auto', maxHeight: '420px' }}>
        {isLoading ? (
          <div className="empty-state">
            <div style={{ color: 'var(--accent-cyan)' }}>Loading tracked targets...</div>
          </div>
        ) : error ? (
          <div className="empty-state">
            <AlertCircle size={28} style={{ color: 'var(--color-high-risk)' }} />
            <div className="empty-state-text" style={{ color: 'var(--color-high-risk)' }}>Target Feed Unavailable</div>
            <div className="empty-state-sub">{error}</div>
          </div>
        ) : safeTargets.length === 0 ? (
          <div className="empty-state">
            <AlertCircle size={28} />
            <div className="empty-state-text">No Active Targets</div>
            <div className="empty-state-sub">Zero targets detected in current sequence window.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {safeTargets.map((target, idx) => {
              const targetId = target?.target_id ?? idx;
              const confidencePct = target?.confidence !== undefined ? (target.confidence * 100).toFixed(1) : '0.0';
              const riskLevel = target?.risk?.level || 'NORMAL';
              const riskScore = target?.risk?.score ?? 0;
              const centerCoords = target?.center ? `[${target.center[0] ?? 0}, ${target.center[1] ?? 0}]` : '[0, 0]';
              const directionStr = target?.direction || 'UNKNOWN';
              const zoneStateStr = target?.zone_state || 'OUTSIDE';
              const riskFactors = target?.risk?.factors || [];

              return (
                <div
                  key={targetId}
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    padding: '0.75rem',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.5rem'
                  }}
                >
                  {/* Header: Target ID + Risk Badge */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>Target #{targetId}</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                        (Conf: {confidencePct}%)
                      </span>
                    </div>
                    <span className={getRiskBadgeClass(riskLevel)}>
                      Risk: {riskScore} [{riskLevel}]
                    </span>
                  </div>

                  {/* Grid Info: Center, Direction, Zone State */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MapPin size={12} style={{ color: 'var(--accent-cyan)' }} />
                      <span>Center: {centerCoords}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Compass size={12} style={{ color: 'var(--accent-cyan)' }} />
                      <span>Dir: {directionStr}</span>
                    </div>
                  </div>

                  {/* Zone State Indicator */}
                  <div style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Zone Status:</span>
                    <span style={{
                      fontWeight: 600,
                      marginLeft: '6px',
                      color: zoneStateStr === 'INSIDE' ? 'var(--color-high-risk)' : 'var(--color-normal)',
                      fontFamily: 'var(--font-mono)'
                    }}>
                      {zoneStateStr}
                    </span>
                  </div>

                  {/* Factors List */}
                  {riskFactors.length > 0 && (
                    <div style={{ marginTop: '0.25rem', paddingTop: '0.4rem', borderTop: '1px dashed var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '2px' }}>Triggered Risk Factors:</div>
                      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {riskFactors.map((f, fIdx) => (
                          <li key={fIdx} style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between' }}>
                            <span>• {f?.name || 'Factor'}</span>
                            <span style={{ color: 'var(--color-monitor)', fontFamily: 'var(--font-mono)' }}>+{f?.points ?? 0} pts</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default TargetOverview;

