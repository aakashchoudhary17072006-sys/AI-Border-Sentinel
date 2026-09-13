import React from 'react';
import { Cpu, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { StatusResponse, HealthResponse } from '../../types/api';
import apiService from '../../services/api';

interface SystemStatusProps {
  statusData: StatusResponse | null;
  healthData: HealthResponse | null;
  isLoading?: boolean;
  error?: string | null;
}

export const SystemStatus: React.FC<SystemStatusProps> = ({ statusData, healthData, isLoading, error }) => {
  const isBackendOnline = Boolean(healthData && (healthData.status === 'ok' || healthData.status === 'healthy'));

  const modules = [
    {
      name: 'FastAPI REST Service',
      sub: isBackendOnline ? `Version ${healthData?.version || '1.0.0'} • ${apiService.getBaseUrl()}` : 'Backend Connection Offline',
      online: isBackendOnline
    },
    {
      name: 'Person Detection Engine',
      sub: 'YOLOv8n Thermal Detector',
      online: isBackendOnline
    },
    {
      name: 'Multi-Object Tracker',
      sub: 'ByteTrack MOT Persistent IDs',
      online: isBackendOnline
    },
    {
      name: 'Explainable Risk Engine',
      sub: '0–100 Rule-Based Heuristic',
      online: isBackendOnline
    },
    {
      name: 'Telemetry Artifact Data',
      sub: statusData ? `Sequence: ${statusData?.sequence || 'patrol1_final'} (${statusData?.processed_frames ?? 0} frames)` : 'Sequence Data Feed',
      online: Boolean(statusData?.telemetry_available)
    }
  ];


  return (
    <div className="panel">
      <div className="panel-header">
        <span className="panel-title">
          <Cpu size={16} /> Pipeline System Status
        </span>
        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          MODULE HEALTH
        </span>
      </div>

      <div className="panel-body">
        {isLoading ? (
          <div className="empty-state">
            <RefreshCw size={24} className="spin" style={{ color: 'var(--accent-cyan)' }} />
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Polling Pipeline Status...</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {modules.map((mod, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.5rem 0.75rem',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '6px',
                  border: '1px solid var(--border-subtle)'
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                    {mod.name}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    {mod.sub}
                  </div>
                </div>

                {mod.online ? (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      color: 'var(--color-normal)',
                      fontFamily: 'var(--font-mono)'
                    }}
                  >
                    <CheckCircle2 size={12} /> ONLINE
                  </span>
                ) : (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      color: 'var(--color-high-risk)',
                      fontFamily: 'var(--font-mono)'
                    }}
                  >
                    <AlertTriangle size={12} /> DISCONNECTED
                  </span>
                )}
              </div>
            ))}
            {error && (
              <div style={{ fontSize: '0.72rem', color: 'var(--color-high-risk)', marginTop: '0.25rem' }}>
                System Error: {error}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemStatus;
