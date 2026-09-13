import React from 'react';
import { ShieldAlert, Radio } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="header-bar">
      <div className="header-brand">
        <div className="header-icon">
          <ShieldAlert size={26} />
        </div>
        <div className="header-title-group">
          <h1 className="header-title">AI Border Sentinel</h1>
          <span className="header-subtitle">AI-Powered Thermal Border Surveillance & Risk Monitoring</span>
        </div>
      </div>

      <div className="header-controls">
        <div className="demo-badge">
          <Radio size={14} />
          <span>DEMO MODE • PRE-RECORDED THERMAL DATA</span>
        </div>

        <div className="status-indicator">
          <span className="status-dot"></span>
          <span>SYSTEM OPERATIONAL</span>
        </div>
      </div>
    </header>
  );
};

export default Header;
