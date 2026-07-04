import AppHeader from "../../components/layout/AppHeader";
import Spinner from "../../components/ui/Spinner";
import StatsDashboard from "../../features/stats/components/StatsDashboard";
import { useStats } from "../../features/stats/hooks/useStats";
import "./StatsPage.css";

export default function StatsPage() {
  const {
    data,
    initialLoading,
    refreshing,
    error,
    period,
    lastUpdated,
    setPeriod,
    refresh,
  } = useStats();

  return (
    <div className="stats-page">
      <AppHeader />
      <div className="stats-page-content scrollable">
        {initialLoading ? (
          <Spinner fullPage label="Loading stats..." />
        ) : data ? (
          <StatsDashboard
            data={data}
            period={period}
            refreshing={refreshing}
            lastUpdated={lastUpdated}
            error={error}
            onPeriodChange={setPeriod}
            onRefresh={() => void refresh()}
          />
        ) : (
          <div className="stats-page-empty" role="alert">
            {error || "No stats available."}
          </div>
        )}
      </div>
    </div>
  );
}
