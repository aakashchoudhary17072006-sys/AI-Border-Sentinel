import React from 'react';

export const RiskLegend: React.FC = () => {
  return (
    <div className="risk-legend-bar">
      <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Risk Level Legend:</span>
      <span className="risk-pill normal">NORMAL (0–30)</span>
      <span className="risk-pill monitor">MONITOR (31–60)</span>
      <span className="risk-pill suspicious">SUSPICIOUS (61–80)</span>
      <span className="risk-pill high-risk">HIGH RISK (81–100)</span>
    </div>
  );
};

export default RiskLegend;
