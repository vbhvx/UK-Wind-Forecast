import type { DailyAnalysisResponse, MonthAnalysisResponse, HealthResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '';

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) {
    throw new Error(`Health check failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchDailyAnalysis(
  deliveryDate: string,
  cutoffTime: string = '10:00',
  dayAhead: boolean = true
): Promise<DailyAnalysisResponse> {
  const params = new URLSearchParams({
    delivery_date: deliveryDate,
    cutoff_time: cutoffTime,
    day_ahead: String(dayAhead),
  });

  const res = await fetch(`${API_BASE}/api/analysis?${params.toString()}`);
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: 'Unknown network error' }));
    throw new Error(errorBody.detail || `Server error (${res.status})`);
  }
  return res.json();
}

export async function fetchMonthlyAnalysis(cutoffTime: string = '10:00'): Promise<MonthAnalysisResponse> {
  const params = new URLSearchParams({
    cutoff_time: cutoffTime,
  });

  const res = await fetch(`${API_BASE}/api/month?${params.toString()}`);
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: 'Unknown network error' }));
    throw new Error(errorBody.detail || `Server error (${res.status})`);
  }
  return res.json();
}
