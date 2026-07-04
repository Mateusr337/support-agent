import { apiRequest } from "./api";
import type { GetStatsMetricsParams, StatsMetricsResponse } from "../types/api/stats";

export const statsService = {
  getMetrics(params: GetStatsMetricsParams = {}): Promise<StatsMetricsResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set("period", params.period ?? "today");
    if (params.sessionId) {
      searchParams.set("session_id", params.sessionId);
    }
    if (params.turnId) {
      searchParams.set("turn_id", params.turnId);
    }
    return apiRequest<StatsMetricsResponse>(`/api/v1/stats/metrics?${searchParams}`);
  },
};
