import React from 'react';
import {
  ResponsiveContainer,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ComposedChart,
  Cell,
} from 'recharts';
import { BarChart3 } from 'lucide-react';
import type { MonthAnalysisResponse, DaySummary } from '../types';

interface SectionCMonthTrendProps {
  monthData: MonthAnalysisResponse | null;
  selectedDate: string;
  onSelectDate: (date: string) => void;
  isLoading: boolean;
}

interface CustomTrendTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

const CustomTrendTooltip: React.FC<CustomTrendTooltipProps> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const d: DaySummary = payload[0]?.payload;
    return (
      <div className="custom-tooltip">
        <div className="tooltip-header">{d.date}</div>
        <div className="tooltip-row">
          <span style={{ color: '#38bdf8' }}>Daily MAE:</span>
          <span className="tooltip-val" style={{ color: '#38bdf8' }}>
            {d.mae !== null ? `${d.mae.toLocaleString()} MW` : 'No Data'}
          </span>
        </div>
        <div className="tooltip-row">
          <span style={{ color: '#10b981' }}>Coverage:</span>
          <span className="tooltip-val" style={{ color: '#10b981' }}>
            {Math.round(d.coverage * 100)}% ({d.matchedPeriods}/{d.actualPeriods})
          </span>
        </div>
        {d.bias !== null && (
          <div className="tooltip-row">
            <span style={{ color: '#94a3b8' }}>Daily Bias:</span>
            <span className="tooltip-val" style={{ color: d.bias > 0 ? '#fb7185' : '#34d399' }}>
              {d.bias > 0 ? `+${d.bias.toLocaleString()}` : d.bias.toLocaleString()} MW
            </span>
          </div>
        )}
        <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '6px' }}>
          Click bar to view full day details
        </div>
      </div>
    );
  }
  return null;
};

export const SectionC_MonthTrend: React.FC<SectionCMonthTrendProps> = ({
  monthData,
  selectedDate,
  onSelectDate,
  isLoading,
}) => {
  if (isLoading && !monthData) {
    return (
      <div className="glass-card" style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!monthData) return null;

  const chartData = monthData.days.map((d) => ({
    ...d,
    dayLabel: `Jan ${parseInt(d.date.split('-')[2], 10)}`,
    coveragePct: Math.round(d.coverage * 100),
  }));

  const overall = monthData.overallMetrics;

  return (
    <div className="glass-card">
      <div className="section-header">
        <div>
          <h2 className="section-title">
            <BarChart3 size={20} color="#a855f7" />
            Section C: January 2026 Accuracy Trend
          </h2>
          <p className="section-subtitle">
            Daily day-ahead evaluation metrics across January 2026 · Click any date to inspect
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="badge badge-dim">
            <span>Overall MAE:</span>
            <strong style={{ color: '#38bdf8' }}>{overall.mae?.toLocaleString()} MW</strong>
          </div>
          <div className="badge badge-dim">
            <span>Systematic Bias:</span>
            <strong style={{ color: overall.bias && overall.bias > 0 ? '#fb7185' : '#34d399' }}>
              {overall.bias && overall.bias > 0 ? `+${overall.bias.toLocaleString()}` : overall.bias?.toLocaleString()} MW
            </strong>
          </div>
          <div className="badge badge-dim">
            <span>Matched:</span>
            <strong>{overall.matchedPeriods} / {overall.actualPeriods} Periods</strong>
          </div>
        </div>
      </div>

      <div className="chart-container" style={{ height: '320px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 15, right: 25, left: 10, bottom: 25 }}
            onClick={(state: any) => {
              if (state && state.activePayload && state.activePayload.length) {
                const clickedDate = state.activePayload[0].payload.date;
                if (clickedDate) onSelectDate(clickedDate);
              }
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.06)" />
            <XAxis
              dataKey="dayLabel"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              interval={2}
              tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            {/* Left YAxis: MAE in MW */}
            <YAxis
              yAxisId="left"
              stroke="#64748b"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
              unit=" MW"
              width={65}
              tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            {/* Right YAxis: Coverage in % */}
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              stroke="#64748b"
              tick={{ fill: '#10b981', fontSize: 11 }}
              unit="%"
              width={45}
              tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <Tooltip content={<CustomTrendTooltip />} />

            {/* Daily MAE Bar */}
            <Bar yAxisId="left" dataKey="mae" name="Daily MAE (MW)" radius={[4, 4, 0, 0]}>
              {chartData.map((entry) => {
                const isSelected = entry.date === selectedDate;
                return (
                  <Cell
                    key={`cell-${entry.date}`}
                    fill={isSelected ? '#38bdf8' : 'rgba(56, 189, 248, 0.45)'}
                    stroke={isSelected ? '#fff' : 'transparent'}
                    strokeWidth={isSelected ? 1.5 : 0}
                    style={{ cursor: 'pointer' }}
                  />
                );
              })}
            </Bar>

            {/* Daily Coverage Line */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="coveragePct"
              name="Coverage (%)"
              stroke="#10b981"
              strokeWidth={2}
              dot={{ r: 2, fill: '#10b981' }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '12px', fontSize: '0.75rem', color: '#64748b' }}>
        <span>Selected date is highlighted in vibrant cyan. Click any bar to toggle the dashboard snapshot.</span>
        <span>Bars: Daily MAE (MW) · Green Line: Matched Coverage (%)</span>
      </div>
    </div>
  );
};
