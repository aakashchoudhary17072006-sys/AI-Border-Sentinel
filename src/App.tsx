import React, { useState } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import Dashboard from './pages/Dashboard';

export const App: React.FC = () => {
  const [activeSection, setActiveSection] = useState('overview');

  const handleSelectSection = (sectionId: string) => {
    setActiveSection(sectionId);
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="app-container">
      <Header />
      <div className="main-layout">
        <Sidebar activeSection={activeSection} onSelectSection={handleSelectSection} />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Dashboard />
        </main>
      </div>
    </div>
  );
};

export default App;
