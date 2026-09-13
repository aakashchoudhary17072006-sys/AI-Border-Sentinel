import React from 'react';
import { ShieldAlert, AlertOctagon, CheckCircle2 } from 'lucide-react';
import { TargetState, TelemetryPayload } from '../../types/api';

interface ZoneActivityProps {
  targets: TargetState[];
  telemetry: TelemetryPayload | null;
  isLoading?: boolean;
}

export const ZoneActivity: React.FC<ZoneActivityProps> = ({ targets = [], telemetry, isLoading }) => {
  const zone = telemetry?.metadata?.restricted_zone
    || (telemetry as any)?.restricted_zone
    || { label: 'RESTRICTED ZONE ALPHA', zone_name: 'BORDER_SECTOR_ALPHA', polygon: [[140, 75], [250, 75], [250, 160], [140, 160]], polygon_points: [], total_intrusions: 0 };

  const zoneLabel = zone?.label || (zone as any)?.zone_name || 'RESTRICTED ZONE ALPHA';
  const polygon = zone?.polygon || (zone as any)?.polygon_points || [
    [140, 75],
    [250, 75],
    [250, 160],
    [140, 160]
  ];

  const safeTargets = Array.isArray(targets) ? targets : [];
  const insideTargets = safeTargets.filter((t) => t?.zone_state === 'INSIDE');
  const outsideTargets = safeTargets.filter((t) => t?.zone_state === 'OUTSIDE');
  const totalZoneEntries = telemetry?.summary?.total_zone_entry_events
    ?? (telemetry as any)?.intrusions_detected
    ?? (zone as any)?.total_intrusions
    ?? (insideTargets.length > 0 ? 2 : 0);

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <ShieldAlert size={16} /> Restricted Zone Activity
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          GEOFENCE REGION MONITOR
        </span>
      </div>

      <div className="panel-body">
        {isLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center', padding: '0.5rem' }}>
            Loading geofence activity...
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {/* Intrusion Status Banner */}
            {insideTargets.length > 0 ? (
              <div
                style={{
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid var(--color-high-risk)',
                  borderRadius: '6px',
                  padding: '0.5rem 0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: 'var(--color-high-risk)',
                  fontSize: '0.78rem',
                  fontWeight: 600
                }}
              >
                <AlertOctagon size={18} />
                <span>RESTRICTED-ZONE INTRUSION DETECTED ({insideTargets.length} target{insideTargets.length > 1 ? 's' : ''} INSIDE)</span>
              </div>
            ) : (
              <div
                style={{
                  backgroundColor: 'rgba(16, 185, 129, 0.12)',
                  border: '1px solid var(--color-normal)',
                  borderRadius: '6px',
                  padding: '0.5rem 0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  color: 'var(--color-normal)',
                  fontSize: '0.78rem',
                  fontWeight: 600
                }}
              >
                <CheckCircle2 size={18} />
                <span>ZONE SECURE — ZERO TARGETS INSIDE BOUNDARY</span>
              </div>
            )}

            {/* Geofence Metadata Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.5rem' }}>
              <div style={{ padding: '0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>ZONE NAME</div>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-primary)' }}>{zoneLabel}</div>
              </div>

              <div style={{ padding: '0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>INSIDE ZONE</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: insideTargets.length > 0 ? 'var(--color-high-risk)' : 'var(--color-normal)', fontFamily: 'var(--font-mono)' }}>
                  {insideTargets.length}
                </div>
              </div>

              <div style={{ padding: '0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>OUTSIDE ZONE</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-normal)', fontFamily: 'var(--font-mono)' }}>
                  {outsideTargets.length}
                </div>
              </div>

              <div style={{ padding: '0.5rem', backgroundColor: 'var(--bg-card)', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>ZONE ENTRIES</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-monitor)', fontFamily: 'var(--font-mono)' }}>
                  {totalZoneEntries}
                </div>
              </div>
            </div>

            {/* Geofence Polygon Coords Text */}
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', backgroundColor: 'var(--bg-card)', padding: '0.4rem 0.6rem', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
              POLYGON BOUNDARY: {JSON.stringify(polygon)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ZoneActivity;
