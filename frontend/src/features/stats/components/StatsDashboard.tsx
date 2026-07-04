import type { HistogramBucketResponse, SpreadStatsResponse } from "../../../types/api/stats";
import "./StatsDashboard.css";

interface StatsDashboardProps {
  data: NonNullable<import("../../../types/api/stats").StatsMetricsResponse>;
  period: "today" | "week";
  refreshing: boolean;
  lastUpdated: Date | null;
  error: string;
  onPeriodChange: (period: "today" | "week") => void;
  onRefresh: () => void;
}

function formatNumber(value: number): string {
  return value.toLocaleString();
}

function formatMs(value: number | null): string {
  if (value === null) {
    return "—";
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}s`;
  }
  return `${value}ms`;
}

function formatBucketLabel(start: number, end: number | null): string {
  if (end === null) {
    return `${formatNumber(start)}+`;
  }
  return `${formatNumber(start)}–${formatNumber(end)}`;
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="stats-kpi-card">
      <span className="stats-kpi-value">{value}</span>
      <span className="stats-kpi-label">{label}</span>
    </div>
  );
}

function SpreadPanel({
  title,
  spread,
}: {
  title: string;
  spread: SpreadStatsResponse | null;
}) {
  return (
    <div className="stats-spread-panel">
      <h3>{title}</h3>
      {spread ? (
        <dl className="stats-spread-grid">
          <div>
            <dt>Min</dt>
            <dd>{formatNumber(spread.min)}</dd>
          </div>
          <div>
            <dt>P50</dt>
            <dd>{formatNumber(spread.p50)}</dd>
          </div>
          <div>
            <dt>P95</dt>
            <dd>{formatNumber(spread.p95)}</dd>
          </div>
          <div>
            <dt>Max</dt>
            <dd>{formatNumber(spread.max)}</dd>
          </div>
        </dl>
      ) : (
        <p className="stats-empty">No data in this period.</p>
      )}
    </div>
  );
}

function HistogramChart({
  title,
  buckets,
}: {
  title: string;
  buckets: HistogramBucketResponse[];
}) {
  const maxCount = Math.max(...buckets.map((bucket) => bucket.count), 1);

  return (
    <div className="stats-chart-panel">
      <h3>{title}</h3>
      <div className="stats-histogram">
        {buckets.map((bucket) => (
          <div key={`${bucket.bucket_start}-${bucket.bucket_end ?? "max"}`} className="stats-histogram-row">
            <span className="stats-histogram-label">
              {formatBucketLabel(bucket.bucket_start, bucket.bucket_end)}
            </span>
            <div className="stats-histogram-bar-track">
              <div
                className="stats-histogram-bar-fill"
                style={{ width: `${(bucket.count / maxCount) * 100}%` }}
              />
            </div>
            <span className="stats-histogram-count">{bucket.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StatsDashboard({
  data,
  period,
  refreshing,
  lastUpdated,
  error,
  onPeriodChange,
  onRefresh,
}: StatsDashboardProps) {
  const maxDayTokens = Math.max(...data.tokens_by_day.map((day) => day.total_tokens), 1);

  return (
    <div className="stats-dashboard">
      <div className="stats-toolbar">
        <div>
          <h2>Usage stats</h2>
          {lastUpdated && (
            <p className="stats-updated">
              Updated {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="stats-toolbar-actions">
          <div className="stats-period-toggle" role="group" aria-label="Period">
            <button
              type="button"
              className={period === "today" ? "active" : ""}
              onClick={() => onPeriodChange("today")}
            >
              Today
            </button>
            <button
              type="button"
              className={period === "week" ? "active" : ""}
              onClick={() => onPeriodChange("week")}
            >
              Week
            </button>
          </div>
          <button
            type="button"
            className="stats-refresh-btn"
            onClick={onRefresh}
            disabled={refreshing}
            aria-busy={refreshing}
          >
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {refreshing && <div className="stats-refresh-bar" aria-hidden="true" />}

      {error && (
        <div className="stats-error" role="alert">
          {error}
        </div>
      )}

      <div className="stats-kpi-grid">
        <KpiCard label="Total tokens" value={formatNumber(data.summary.total_tokens)} />
        <KpiCard
          label="Avg tokens / turn"
          value={data.tokens.per_turn_avg !== null ? formatNumber(data.tokens.per_turn_avg) : "—"}
        />
        <KpiCard
          label="Avg tokens / session"
          value={data.tokens.per_session_avg !== null ? formatNumber(data.tokens.per_session_avg) : "—"}
        />
        <KpiCard label="Turns" value={formatNumber(data.summary.turn_count)} />
        <KpiCard label="Avg turn latency" value={formatMs(data.latency_ms.turn_avg_ms)} />
        <KpiCard label="Avg LLM call" value={formatMs(data.latency_ms.llm_call_avg_ms)} />
        <KpiCard label="Avg tool call" value={formatMs(data.latency_ms.tool_call_avg_ms)} />
        <KpiCard label="Sessions" value={formatNumber(data.summary.session_count)} />
      </div>

      <div className="stats-chart-panel stats-tokens-by-day">
        <h3>Tokens by day</h3>
        {data.tokens_by_day.length > 0 ? (
          <div className="stats-day-chart">
            {data.tokens_by_day.map((day) => (
              <div key={day.date} className="stats-day-column">
                <div className="stats-day-bar-track">
                  <div
                    className="stats-day-bar-fill"
                    style={{ height: `${(day.total_tokens / maxDayTokens) * 100}%` }}
                    title={`${formatNumber(day.total_tokens)} tokens`}
                  />
                </div>
                <span className="stats-day-label">{day.date.slice(5)}</span>
                <span className="stats-day-value">{formatNumber(day.total_tokens)}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="stats-empty">No token usage in this period.</p>
        )}
      </div>

      <div className="stats-spread-row">
        <SpreadPanel title="Tokens per turn" spread={data.tokens.per_turn_spread} />
        <SpreadPanel title="Tokens per session" spread={data.tokens.per_session_spread} />
      </div>

      <div className="stats-spread-row">
        <HistogramChart title="Turn token distribution" buckets={data.distributions.tokens_per_turn} />
        <HistogramChart title="Session token distribution" buckets={data.distributions.tokens_per_session} />
      </div>
    </div>
  );
}
