import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { Activity } from 'lucide-react';
import type { DailyAnalysisResponse } from '../types';

interface SectionBForecastChartProps {
  data: DailyAnalysisResponse | null;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const periodData = payload[0]?.payload;
    const actual = periodData?.actual;
    const forecast = periodData?.forecast;
    const error = periodData?.error;
    const pubTime = periodData?.publishTime;
    const sp = periodData?.settlementPeriod;

    return (
      <div className="custom-tooltip">
        <div className="tooltip-header">
          Delivery: {label} UTC {sp ? `· Period ${sp}` : ''}
        </div>

        <div className="tooltip-row">
          <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
            Actual Metered:
          </span>
          <span className="tooltip-val" style={{ color: '#10b981' }}>
            {actual !== null && actual !== undefined ? `${actual.toLocaleString()} MW` : 'N/A'}
          </span>
        </div>

        <div className="tooltip-row">
          <span style={{ color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#38bdf8' }} />
            Selected Forecast:
          </span>
          <span className="tooltip-val" style={{ color: '#38bdf8' }}>
            {forecast !== null && forecast !== undefined ? `${forecast.toLocaleString()} MW` : 'Missing (Gap)'}
          </span>
        </div>

        {error !== null && error !== undefined && (
          <div className="tooltip-row" style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
            <span style={{ color: '#94a3b8' }}>Forecast Miss:</span>
            <span
              className="tooltip-val"
              style={{ color: error > 0 ? '#fb7185' : '#34d399' }}
            >
              {error > 0 ? `+${error.toLocaleString()} MW (Over)` : `${error.toLocaleString()} MW (Under)`}
            </span>
          </div>
        )}

        {pubTime && (
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '6px' }}>
            Vintage Published: {new Date(pubTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' })} UTC
          </div>
        )}
      </div>
    );
  }
  return null;
};

export const SectionB_ForecastChart: React.FC<SectionBForecastChartProps> = ({ data }) => {
  if (!data) return null;

  // Format periods for Recharts
  const chartData = data.periods.map((p) => {
    // Extract HH:MM from ISO string e.g. 2026-01-02T14:30:00Z -> 14:30
    const timeLabel = p.startTime.substring(11, 16);
    return {
      time: timeLabel,
      actual: p.actual,
      forecast: p.forecast, // null when missing, Recharts will render gap with connectNulls=false
      error: p.error,
      publishTime: p.publishTime,
      settlementPeriod: p.settlementPeriod,
      status: p.status,
    };
  });

  return (
    <div className="glass-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <Activity size={20} color="#10b981" />
            Section B: Forecast vs Actual Generation
          </h2>
          <p className="section-subtitle">
            30-minute settlement intervals for {data.deliveryDate} · Missing forecast periods shown as gaps
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.8rem', color: '#94a3b8' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '12px', height: '3px', background: '#10b981', borderRadius: '2px' }} />
            <span>Actual Outturn (FUELHH)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '12px', height: '3px', background: '#38bdf8', borderRadius: '2px' }} />
            <span>Eligible Forecast Vintage (WINDFOR)</span>
          </div>
        </div>
      </div>

      <div className="chart-container">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 15, right: 25, left: 10, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
            <XAxis
              dataKey="time"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              interval={3}
              tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <YAxis
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              unit=" MW"
              width={65}
              tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Actual line (continuous across all 48 settlement periods) */}
            <Line
              type="monotone"
              dataKey="actual"
              name="Actual Outturn (MW)"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={{ r: 2, fill: '#10b981' }}
              activeDot={{ r: 6, fill: '#10b981', stroke: '#fff', strokeWidth: 2 }}
              connectNulls={false}
            />

            {/* Forecast line (connectNulls=false to accurately show hourly vintage coverage gaps) */}
            <Line
              type="monotone"
              dataKey="forecast"
              name="Selected Forecast (MW)"
              stroke="#38bdf8"
              strokeWidth={2.5}
              strokeDasharray="4 2"
              dot={{ r: 3, fill: '#38bdf8' }}
              activeDot={{ r: 6, fill: '#38bdf8', stroke: '#fff', strokeWidth: 2 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', fontSize: '0.75rem', color: '#64748b' }}>
        <span>Note: WINDFOR provides hourly resolution points; periods without forecasts represent legitimate missing data, not zero generation.</span>
        <span>Resolution: 30 minutes / Half-hourly</span>
      </div>
    </div>
  );
};
