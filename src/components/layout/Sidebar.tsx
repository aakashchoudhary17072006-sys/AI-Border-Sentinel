import React from 'react';
import { LayoutDashboard, Camera, Users, Bell, Cpu } from 'lucide-react';

interface SidebarProps {
  activeSection?: string;
  onSelectSection?: (sectionId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeSection = 'overview',
  onSelectSection
}) => {
  const handleNavClick = (sectionId: string) => {
    if (onSelectSection) {
      onSelectSection(sectionId);
    } else {
      const element = document.getElementById(`section-${sectionId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  };

  return (
    <aside className="sidebar">
      <ul className="nav-list">
        <li>
          <button
            className={`nav-item ${activeSection === 'overview' ? 'active' : ''}`}
            onClick={() => handleNavClick('overview')}
            aria-current={activeSection === 'overview' ? 'page' : undefined}
          >
            <LayoutDashboard size={18} />
            <span className="nav-text">Overview</span>
          </button>
        </li>
        <li>
          <button
            className={`nav-item ${activeSection === 'surveillance' ? 'active' : ''}`}
            onClick={() => handleNavClick('surveillance')}
            aria-current={activeSection === 'surveillance' ? 'page' : undefined}
          >
            <Camera size={18} />
            <span className="nav-text">Surveillance</span>
          </button>
        </li>
        <li>
          <button
            className={`nav-item ${activeSection === 'targets' ? 'active' : ''}`}
            onClick={() => handleNavClick('targets')}
            aria-current={activeSection === 'targets' ? 'page' : undefined}
          >
            <Users size={18} />
            <span className="nav-text">Targets</span>
          </button>
        </li>
        <li>
          <button
            className={`nav-item ${activeSection === 'alerts' ? 'active' : ''}`}
            onClick={() => handleNavClick('alerts')}
            aria-current={activeSection === 'alerts' ? 'page' : undefined}
          >
            <Bell size={18} />
            <span className="nav-text">Alerts</span>
          </button>
        </li>
        <li>
          <button
            className={`nav-item ${activeSection === 'system' ? 'active' : ''}`}
            onClick={() => handleNavClick('system')}
            aria-current={activeSection === 'system' ? 'page' : undefined}
          >
            <Cpu size={18} />
            <span className="nav-text">System</span>
          </button>
        </li>
      </ul>

      <div className="sidebar-footer">
        <div style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>AI Border Sentinel</div>
        <div>Human-in-the-loop system</div>
      </div>
    </aside>
  );
};

export default Sidebar;
