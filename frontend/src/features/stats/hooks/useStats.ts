import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../../../services/api";
import { statsService } from "../../../services/statsService";
import type { StatsMetricsResponse, StatsPeriodPreset } from "../../../types/api/stats";

export interface UseStatsReturn {
  data: StatsMetricsResponse | null;
  initialLoading: boolean;
  refreshing: boolean;
  error: string;
  period: StatsPeriodPreset;
  lastUpdated: Date | null;
  setPeriod: (period: StatsPeriodPreset) => void;
  refresh: () => Promise<void>;
}

export function useStats(): UseStatsReturn {
  const [data, setData] = useState<StatsMetricsResponse | null>(null);
  const [period, setPeriod] = useState<StatsPeriodPreset>("today");
  const [initialLoading, setInitialLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const hasLoadedRef = useRef(false);

  const loadMetrics = useCallback(
    async (options: { background: boolean }) => {
      if (options.background) {
        setRefreshing(true);
      } else {
        setInitialLoading(true);
      }
      setError("");

      try {
        const metrics = await statsService.getMetrics({ period });
        setData(metrics);
        setLastUpdated(new Date());
        hasLoadedRef.current = true;
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Unable to load stats. Please try again."
        );
      } finally {
        if (options.background) {
          setRefreshing(false);
        } else {
          setInitialLoading(false);
        }
      }
    },
    [period]
  );

  useEffect(() => {
    void loadMetrics({ background: hasLoadedRef.current });
  }, [period, loadMetrics]);

  const refresh = useCallback(async () => {
    await loadMetrics({ background: true });
  }, [loadMetrics]);

  return {
    data,
    initialLoading,
    refreshing,
    error,
    period,
    lastUpdated,
    setPeriod,
    refresh,
  };
}
