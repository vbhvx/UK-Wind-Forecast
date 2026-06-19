import React from 'react';
import { Wind, ShieldCheck, Activity, Database } from 'lucide-react';
import type { HealthResponse } from '../types';

interface HeaderProps {
  health: HealthResponse | null;
  healthLoading: boolean;
}

export const Header: React.FC<HeaderProps> = ({ health, healthLoading }) => {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon-box">
          <Wind size={24} />
        </div>
        <div>
          <h1 className="brand-title">Windward</h1>
          <p className="brand-subtitle">
            Day-Ahead Historical Replay & Decision Accuracy Evaluation · January 2026
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span className="badge badge-cyan" title="Source: Elexon BMRS Insights API (FUELHH & WINDFOR)">
          <Database size={13} />
          Elexon BMRS Live
        </span>
        <span className="badge badge-emerald" title="Zero lookahead leakage mathematically verified">
          <ShieldCheck size={13} />
          Audited Replay
        </span>
        <div className="badge badge-dim" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={13} color={health?.status === 'ok' ? '#10b981' : '#f59e0b'} />
          <span>{healthLoading ? 'Connecting...' : (health?.status === 'ok' ? 'API Online' : 'API Standby')}</span>
        </div>
      </div>
    </header>
  );
};
