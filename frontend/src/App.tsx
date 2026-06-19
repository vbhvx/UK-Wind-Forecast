import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { ControlsBar } from './components/ControlsBar';
import { SectionA_Snapshot } from './components/SectionA_Snapshot';
import { SectionB_ForecastChart } from './components/SectionB_ForecastChart';
import { SectionC_MonthTrend } from './components/SectionC_MonthTrend';
import { SectionD_AuditTable } from './components/SectionD_AuditTable';
import { fetchHealth, fetchDailyAnalysis, fetchMonthlyAnalysis } from './api/client';
import type { DailyAnalysisResponse, MonthAnalysisResponse, HealthResponse } from './types';
import { AlertTriangle, Cpu } from 'lucide-react';

export const App: React.FC = () => {
  const [deliveryDate, setDeliveryDate] = useState<string>('2026-01-02');
  const [cutoffTime, setCutoffTime] = useState<string>('10:00');
  const [dayAhead, setDayAhead] = useState<boolean>(true);

  const [dailyData, setDailyData] = useState<DailyAnalysisResponse | null>(null);
  const [monthData, setMonthData] = useState<MonthAnalysisResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [loadingDaily, setLoadingDaily] = useState<boolean>(true);
  const [loadingMonth, setLoadingMonth] = useState<boolean>(true);
  const [loadingHealth, setLoadingHealth] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Initial health check
  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealth(h);
        setLoadingHealth(false);
      })
      .catch((err) => {
        console.warn('Health check warning:', err);
        setLoadingHealth(false);
      });
  }, []);

  // Fetch daily analysis on parameter change
  const loadDaily = (date: string, cutoff: string, da: boolean) => {
    setLoadingDaily(true);
    setErrorMessage(null);
    fetchDailyAnalysis(date, cutoff, da)
      .then((data) => {
        setDailyData(data);
        setLoadingDaily(false);
      })
      .catch((err) => {
        console.error('Daily analysis failed:', err);
        setErrorMessage(err.message || 'Failed to load daily forecast analysis');
        setLoadingDaily(false);
      });
  };

  // Fetch monthly analysis on cutoff change
  const loadMonth = (cutoff: string) => {
    setLoadingMonth(true);
    fetchMonthlyAnalysis(cutoff)
      .then((m) => {
        setMonthData(m);
        setLoadingMonth(false);
      })
      .catch((err) => {
        console.error('Monthly analysis failed:', err);
        setLoadingMonth(false);
      });
  };

  useEffect(() => {
    loadDaily(deliveryDate, cutoffTime, dayAhead);
  }, [deliveryDate, cutoffTime, dayAhead]);

  useEffect(() => {
    loadMonth(cutoffTime);
  }, [cutoffTime]);

  const handleRefresh = () => {
    loadDaily(deliveryDate, cutoffTime, dayAhead);
    loadMonth(cutoffTime);
  };

  return (
    <div className="app-container">
      {/* App Header */}
      <Header health={health} healthLoading={loadingHealth} />

      {/* Interactive Controls Bar */}
      <ControlsBar
        deliveryDate={deliveryDate}
        onDateChange={setDeliveryDate}
        cutoffTime={cutoffTime}
        onCutoffChange={setCutoffTime}
        dayAhead={dayAhead}
        onDayAheadChange={setDayAhead}
        onRefresh={handleRefresh}
        isLoading={loadingDaily || loadingMonth}
      />

      {/* Error Banner */}
      {errorMessage && (
        <div className="error-banner">
          <AlertTriangle size={20} style={{ flexShrink: 0 }} />
          <div>
            <strong>Analysis Error:</strong> {errorMessage}
            <div style={{ fontSize: '0.8rem', opacity: 0.9, marginTop: '2px' }}>
              Check API status or verify parameters. Upstream Elexon failures are visibly captured without fabricating data.
            </div>
          </div>
        </div>
      )}

      {/* Section A: Decision Snapshot */}
      <SectionA_Snapshot data={dailyData} />

      {/* Section B: Forecast vs Actual Line Chart */}
      <SectionB_ForecastChart data={dailyData} />

      {/* Section C: January Accuracy Trend */}
      <SectionC_MonthTrend
        monthData={monthData}
        selectedDate={deliveryDate}
        onSelectDate={setDeliveryDate}
        isLoading={loadingMonth}
      />

      {/* Section D: Period-Level Audit Table & CSV */}
      <SectionD_AuditTable data={dailyData} />

      {/* Footer & Audit Disclosures */}
      <footer
        style={{
          marginTop: '20px',
          paddingTop: '24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
          fontSize: '0.8rem',
          color: '#64748b',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Cpu size={15} color="#38bdf8" />
          <span>Windward · BMRS Analytics Platform</span>
        </div>
        <div>
          Data Source: Elexon BMRS (FUELHH Actuals & WINDFOR Forecast Streams) · Scope: January 2026
        </div>
      </footer>
    </div>
  );
};

export default App;
