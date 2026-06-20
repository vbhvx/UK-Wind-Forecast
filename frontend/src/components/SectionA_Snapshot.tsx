import React from 'react';
import { Target, TrendingUp, Compass, CheckCircle2, AlertTriangle, Clock, Info } from 'lucide-react';
import type { DailyAnalysisResponse } from '../types';

interface SectionASnapshotProps {
  data: DailyAnalysisResponse | null;
}

export const SectionA_Snapshot: React.FC<SectionASnapshotProps> = ({ data }) => {
  if (!data) return null;

  const metrics = data.metrics;
  const coveragePct = Math.round(metrics.coverage * 100);

  return (
    <div className="glass-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <Target size={20} color="#38bdf8" />
            Section A: Decision Snapshot
          </h2>
          <p className="section-subtitle">
            Historical day-ahead purchasing decision evaluation for {data.deliveryDate}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          <span className="badge badge-cyan" title="Auditable publication vintage">
            <Clock size={13} />
            Latest Selected Pub: {data.latestSelectedPublication ? new Date(data.latestSelectedPublication).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' }) + ' UTC' : 'None'}
          </span>
          <span className={`badge ${coveragePct >= 50 ? 'badge-emerald' : 'badge-amber'}`}>
            <CheckCircle2 size={13} />
            Coverage: {coveragePct}% ({metrics.matchedPeriods}/{metrics.actualPeriods} Periods)
          </span>
        </div>
      </div>

      {/* Auditable Decision Cutoff Assumption Banner */}
      <div
        style={{
          background: 'rgba(56, 189, 248, 0.07)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          fontSize: '0.85rem',
          lineHeight: 1.5,
          color: '#bae6fd',
        }}
      >
        <Info size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#38bdf8' }} />
        <div>
          <strong>Decision Cutoff Assumption:</strong> {data.cutoffAssumption}
          <div style={{ fontSize: '0.78rem', color: '#7dd3fc', marginTop: '4px' }}>
            Mathematical formulation: <code>p*(t, c) = max&#123;p : p ≤ c&#125;</code>. Any publication after {data.cutoffTimestampUtc} is excluded to guarantee zero lookahead leakage into trading decisions.
          </div>
        </div>
      </div>

      {/* 5 Core Metric Cards */}
      <div className="metrics-grid">
        {/* MAE */}
        <div className="metric-card" style={{ '--card-accent': '#38bdf8' } as React.CSSProperties}>
          <div className="metric-label">
            <span>Mean Absolute Error</span>
            <TrendingUp size={15} color="#38bdf8" />
          </div>
          <div className="metric-value-container">
            <span className="metric-value">{metrics.mae !== null ? metrics.mae.toLocaleString() : '—'}</span>
            <span className="metric-unit">MW</span>
          </div>
          <div className="metric-desc">Average magnitude of delivery forecast error across matched periods.</div>
        </div>

        {/* RMSE */}
        <div className="metric-card" style={{ '--card-accent': '#a855f7' } as React.CSSProperties}>
          <div className="metric-label">
            <span>Root Mean Squared Error</span>
            <TrendingUp size={15} color="#a855f7" />
          </div>
          <div className="metric-value-container">
            <span className="metric-value">{metrics.rmse !== null ? metrics.rmse.toLocaleString() : '—'}</span>
            <span className="metric-unit">MW</span>
          </div>
          <div className="metric-desc">Penalizes extreme forecast swings and volatility heavily.</div>
        </div>

        {/* Bias */}
        <div className="metric-card" style={{ '--card-accent': metrics.bias && metrics.bias > 0 ? '#f43f5e' : '#10b981' } as React.CSSProperties}>
          <div className="metric-label">
            <span>Systematic Bias</span>
            <Compass size={15} color={metrics.bias && metrics.bias > 0 ? '#f43f5e' : '#10b981'} />
          </div>
          <div className="metric-value-container">
            <span className="metric-value" style={{ color: metrics.bias && metrics.bias > 0 ? '#fb7185' : '#34d399' }}>
              {metrics.bias !== null ? (metrics.bias > 0 ? `+${metrics.bias.toLocaleString()}` : metrics.bias.toLocaleString()) : '—'}
            </span>
            <span className="metric-unit">MW</span>
          </div>
          <div className="metric-desc">
            {metrics.bias && metrics.bias > 0
              ? 'Overforecasting: Forecast exceeded actual generation.'
              : 'Underforecasting: Generation exceeded forecast.'}
          </div>
        </div>

        {/* Max Absolute Error */}
        <div className="metric-card" style={{ '--card-accent': '#f59e0b' } as React.CSSProperties}>
          <div className="metric-label">
            <span>Max Absolute Error</span>
            <AlertTriangle size={15} color="#f59e0b" />
          </div>
          <div className="metric-value-container">
            <span className="metric-value">{metrics.maxAbsoluteError !== null ? metrics.maxAbsoluteError.toLocaleString() : '—'}</span>
            <span className="metric-unit">MW</span>
          </div>
          <div className="metric-desc">Worst single delivery interval forecast miss of the day.</div>
        </div>

        {/* Matched Coverage */}
        <div className="metric-card" style={{ '--card-accent': '#10b981' } as React.CSSProperties}>
          <div className="metric-label">
            <span>Matched Coverage</span>
            <CheckCircle2 size={15} color="#10b981" />
          </div>
          <div className="metric-value-container">
            <span className="metric-value">{coveragePct}%</span>
            <span className="metric-unit">({metrics.matchedPeriods}/{metrics.actualPeriods})</span>
          </div>
          <div className="metric-desc">
            Elexon WINDFOR forecasts are hourly; FUELHH actuals are half-hourly.
          </div>
        </div>
      </div>
    </div>
  );
};
