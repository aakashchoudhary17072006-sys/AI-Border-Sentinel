import React from 'react';

interface SummaryCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  subtext?: string;
}

export const SummaryCard: React.FC<SummaryCardProps> = ({ label, value, icon, subtext }) => {
  return (
    <div className="summary-card">
      <div className="card-info">
        <span className="card-label">{label || ''}</span>
        <span className="card-value">{value ?? '—'}</span>
        {subtext && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{subtext}</span>}
      </div>
      <div className="card-icon-wrapper">
        {icon}
      </div>
    </div>
  );
};


export default SummaryCard;
