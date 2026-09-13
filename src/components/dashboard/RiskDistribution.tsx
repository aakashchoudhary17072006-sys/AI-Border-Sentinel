import React from 'react';
import { BarChart2 } from 'lucide-react';
import { TargetState, StatusResponse } from '../../types/api';

interface RiskDistributionProps {
  targets: TargetState[];
  statusData: StatusResponse | null;
  isLoading?: boolean;
}

export const RiskDistribution: React.FC<RiskDistributionProps> = ({ targets = [], statusData, isLoading }) => {
  const safeTargets = Array.isArray(targets) ? targets : [];

  // Count risk levels from active targets list
  const counts = {
    NORMAL: 0,
    MONITOR: 0,
    SUSPICIOUS: 0,
    'HIGH RISK': 0
  };

  if (safeTargets.length > 0) {
    safeTargets.forEach((t) => {
      const lvl = t?.risk?.level;
      if (lvl && lvl in counts) {
        counts[lvl as keyof typeof counts] += 1;
      }
    });
  } else if (statusData) {
    // Fallback classification if targets list is empty
    const highest = statusData?.highest_risk_level;
    if (highest && highest in counts) {
      counts[highest as keyof typeof counts] = statusData?.unique_targets ?? 0;
    }
  }

  const total = safeTargets.length || statusData?.unique_targets || 0;


  const getPercent = (count: number) => {
    if (total === 0) return 0;
    return Math.round((count / total) * 100);
  };

  const normalPct = getPercent(counts.NORMAL);
  const monitorPct = getPercent(counts.MONITOR);
  const suspiciousPct = getPercent(counts.SUSPICIOUS);
  const highRiskPct = getPercent(counts['HIGH RISK']);

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <BarChart2 size={16} /> Target Risk Distribution
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          HEURISTIC CLASSIFICATION
        </span>
      </div>

      <div className="panel-body">
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '0.5rem' }}>
            Calculating risk distribution...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {/* Multi-Segment Horizontal Distribution Bar */}
            <div
              style={{
                height: '10px',
                width: '100%',
                backgroundColor: 'var(--bg-card)',
                borderRadius: '5px',
                overflow: 'hidden',
                display: 'flex',
                border: '1px solid var(--border-subtle)'
              }}
            >
              {normalPct > 0 && (
                <div
                  style={{ width: `${normalPct}%`, backgroundColor: 'var(--color-normal)' }}
                  title={`NORMAL: ${counts.NORMAL} (${normalPct}%)`}
                />
              )}
              {monitorPct > 0 && (
                <div
                  style={{ width: `${monitorPct}%`, backgroundColor: 'var(--color-monitor)' }}
                  title={`MONITOR: ${counts.MONITOR} (${monitorPct}%)`}
                />
              )}
              {suspiciousPct > 0 && (
                <div
                  style={{ width: `${suspiciousPct}%`, backgroundColor: 'var(--color-suspicious)' }}
                  title={`SUSPICIOUS: ${counts.SUSPICIOUS} (${suspiciousPct}%)`}
                />
              )}
              {highRiskPct > 0 && (
                <div
                  style={{ width: `${highRiskPct}%`, backgroundColor: 'var(--color-high-risk)' }}
                  title={`HIGH RISK: ${counts['HIGH RISK']} (${highRiskPct}%)`}
                />
              )}
              {total === 0 && (
                <div style={{ width: '100%', backgroundColor: 'var(--border-subtle)' }} />
              )}
            </div>

            {/* 4 Risk Tier Summary Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
              <div style={{ padding: '0.4rem 0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>NORMAL</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-normal)', fontFamily: 'var(--font-mono)' }}>
                  {counts.NORMAL}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>0–30 Score</div>
              </div>

              <div style={{ padding: '0.4rem 0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>MONITOR</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-monitor)', fontFamily: 'var(--font-mono)' }}>
                  {counts.MONITOR}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>31–60 Score</div>
              </div>

              <div style={{ padding: '0.4rem 0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>SUSPICIOUS</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-suspicious)', fontFamily: 'var(--font-mono)' }}>
                  {counts.SUSPICIOUS}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>61–80 Score</div>
              </div>

              <div style={{ padding: '0.4rem 0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>HIGH RISK</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-high-risk)', fontFamily: 'var(--font-mono)' }}>
                  {counts['HIGH RISK']}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>81–100 Score</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RiskDistribution;
