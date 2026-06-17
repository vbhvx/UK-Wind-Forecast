export interface PeriodDetail {
  startTime: string;
  settlementPeriod: number | null;
  actual: number | null;
  forecast: number | null;
  publishTime: string | null;
  error: number | null;
  status: 'matched' | 'missing_forecast' | 'missing_actual';
}

export interface MetricsSummary {
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  maxAbsoluteError: number | null;
  matchedPeriods: number;
  actualPeriods: number;
  coverage: number;
}

export interface DailyAnalysisResponse {
  deliveryDate: string;
  cutoffTimeLondon: string;
  cutoffTimestampUtc: string;
  cutoffAssumption: string;
  metrics: MetricsSummary;
  latestSelectedPublication: string | null;
  periods: PeriodDetail[];
}

export interface DaySummary {
  date: string;
  mae: number | null;
  rmse: number | null;
  bias: number | null;
  maxAbsoluteError: number | null;
  matchedPeriods: number;
  actualPeriods: number;
  coverage: number;
  status: 'complete' | 'partial' | 'no_data';
}

export interface MonthAnalysisResponse {
  month: string;
  cutoffTimeLondon: string;
  cutoffAssumption: string;
  overallMetrics: MetricsSummary;
  days: DaySummary[];
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  cacheStatus: Record<string, number>;
}
