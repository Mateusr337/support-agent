export type StatsPeriodPreset = "today" | "week";

export interface StatsPeriodResponse {
  preset: StatsPeriodPreset | null;
  from: string;
  to: string;
}

export interface TokenDayResponse {
  date: string;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface SpreadStatsResponse {
  min: number;
  p50: number;
  p95: number;
  max: number;
  count: number;
}

export interface HistogramBucketResponse {
  bucket_start: number;
  bucket_end: number | null;
  count: number;
}

export interface StatsMetricsResponse {
  period: StatsPeriodResponse;
  summary: {
    total_tokens: number;
    turn_count: number;
    session_count: number;
    llm_call_count: number;
    tool_call_count: number;
  };
  tokens_by_day: TokenDayResponse[];
  latency_ms: {
    turn_avg_ms: number | null;
    llm_call_avg_ms: number | null;
    tool_call_avg_ms: number | null;
  };
  tokens: {
    per_turn_avg: number | null;
    per_session_avg: number | null;
    per_turn_spread: SpreadStatsResponse | null;
    per_session_spread: SpreadStatsResponse | null;
  };
  distributions: {
    tokens_per_turn: HistogramBucketResponse[];
    tokens_per_session: HistogramBucketResponse[];
  };
}

export interface GetStatsMetricsParams {
  period?: StatsPeriodPreset;
  sessionId?: string;
  turnId?: string;
}
