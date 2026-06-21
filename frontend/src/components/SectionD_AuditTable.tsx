import React, { useState } from 'react';
import { Table, Download, CheckCircle, AlertCircle, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { DailyAnalysisResponse } from '../types';

interface SectionDAuditTableProps {
  data: DailyAnalysisResponse | null;
}

export const SectionD_AuditTable: React.FC<SectionDAuditTableProps> = ({ data }) => {
  const [filter, setFilter] = useState<'all' | 'matched' | 'unmatched'>('all');

  if (!data) return null;

  const periods = data.periods;

  const filteredPeriods = periods.filter((p) => {
    if (filter === 'matched') return p.status === 'matched';
    if (filter === 'unmatched') return p.status !== 'matched';
    return true;
  });

  const matchedCount = periods.filter((p) => p.status === 'matched').length;
  const unmatchedCount = periods.length - matchedCount;

  // CSV Export handler
  const handleExportCSV = () => {
    const headers = [
      'SettlementPeriod',
      'StartTimeUTC',
      'ActualGenerationMW',
      'ForecastGenerationMW',
      'ForecastPublishTimeUTC',
      'ForecastErrorMW',
      'Status'
    ];

    const rows = periods.map((p) => [
      p.settlementPeriod ?? '',
      p.startTime,
      p.actual ?? '',
      p.forecast ?? '',
      p.publishTime ?? '',
      p.error ?? '',
      p.status
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `wind_forecast_audit_${data.deliveryDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="glass-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <Table size={20} color="#38bdf8" />
            Section D: Period-Level Audit & Data Lineage
          </h2>
          <p className="section-subtitle">
            Auditable half-hourly observations with source timestamps and error direction
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Filter Pills */}
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              className={`btn btn-pill ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({periods.length})
            </button>
            <button
              className={`btn btn-pill ${filter === 'matched' ? 'active' : ''}`}
              onClick={() => setFilter('matched')}
            >
              Matched ({matchedCount})
            </button>
            <button
              className={`btn btn-pill ${filter === 'unmatched' ? 'active' : ''}`}
              onClick={() => setFilter('unmatched')}
            >
              Missing Forecast ({unmatchedCount})
            </button>
          </div>

          {/* Export CSV button */}
          <button className="btn btn-secondary" onClick={handleExportCSV} title="Export audit dataset as CSV">
            <Download size={14} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      <div className="table-container">
        <table className="audit-table">
          <thead>
            <tr>
              <th>Period</th>
              <th>Delivery Start (UTC)</th>
              <th>Actual Outturn</th>
              <th>Selected Forecast</th>
              <th>Selected Publication (UTC)</th>
              <th>Error (F - A)</th>
              <th>Audit Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredPeriods.map((p, idx) => {
              const hasForecast = p.forecast !== null && p.forecast !== undefined;
              const hasActual = p.actual !== null && p.actual !== undefined;
              const error = p.error;

              return (
                <tr key={p.startTime || idx}>
                  <td className="font-mono" style={{ color: '#94a3b8' }}>
                    {p.settlementPeriod ? `SP ${p.settlementPeriod}` : '—'}
                  </td>
                  <td className="font-mono">
                    {p.startTime.replace('T', ' ').replace('Z', '')}
                  </td>
                  <td className="font-mono" style={{ color: '#10b981', fontWeight: 600 }}>
                    {hasActual ? `${p.actual?.toLocaleString()} MW` : 'Missing'}
                  </td>
                  <td className="font-mono" style={{ color: '#38bdf8', fontWeight: 600 }}>
                    {hasForecast ? `${p.forecast?.toLocaleString()} MW` : '—'}
                  </td>
                  <td className="font-mono" style={{ color: '#64748b', fontSize: '0.8rem' }}>
                    {p.publishTime ? p.publishTime.replace('T', ' ').replace('Z', '') : 'No eligible vintage'}
                  </td>
                  <td className="font-mono" style={{ fontWeight: 700 }}>
                    {error !== null && error !== undefined ? (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          color: error > 0 ? '#fb7185' : '#34d399',
                        }}
                      >
                        {error > 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        {error > 0 ? `+${error.toLocaleString()} MW` : `${error.toLocaleString()} MW`}
                      </span>
                    ) : (
                      <span style={{ color: '#475569' }}>—</span>
                    )}
                  </td>
                  <td>
                    {p.status === 'matched' ? (
                      <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                        <CheckCircle size={11} /> Matched
                      </span>
                    ) : (
                      <span className="badge badge-dim" style={{ fontSize: '0.7rem' }}>
                        <AlertCircle size={11} /> Unmatched Gap
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', fontSize: '0.75rem', color: '#64748b' }}>
        <span>Showing {filteredPeriods.length} of {periods.length} settlement observations</span>
        <span>Audit standard: ISO 8601 UTC normalized timestamps</span>
      </div>
    </div>
  );
};
