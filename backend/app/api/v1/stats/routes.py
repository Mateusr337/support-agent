from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth.dependencies import get_current_user
from app.api.v1.dependencies import get_stats_service
from app.api.v1.responses import UNAUTHORIZED_RESPONSE
from app.api.v1.stats.schemas import (
    HistogramBucketResponse,
    SpreadStatsResponse,
    StatsDistributionsResponse,
    StatsLatencyResponse,
    StatsMetricsResponse,
    StatsPeriodResponse,
    StatsSummaryResponse,
    StatsTokensResponse,
    TokenDayResponse,
)
from app.models.user import User
from app.services.stats_service import InvalidStatsPeriodError, StatsMetrics, StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    response_model=StatsMetricsResponse,
    responses=UNAUTHORIZED_RESPONSE,
)
def get_stats_metrics(
    current_user: User = Depends(get_current_user),
    service: StatsService = Depends(get_stats_service),
    period: str = Query(default="today", pattern="^(today|week)$"),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    session_id: UUID | None = Query(default=None),
    turn_id: UUID | None = Query(default=None),
) -> StatsMetricsResponse:
    try:
        metrics = service.get_metrics(
            user_id=current_user.id,
            period=period,
            from_dt=from_dt,
            to_dt=to_dt,
            session_id=session_id,
            turn_id=turn_id,
        )
    except InvalidStatsPeriodError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _to_response(metrics)


def _to_response(metrics: StatsMetrics) -> StatsMetricsResponse:
    turn_spread = metrics.tokens_per_turn_spread
    session_spread = metrics.tokens_per_session_spread

    return StatsMetricsResponse(
        period=StatsPeriodResponse(
            preset=metrics.period.preset,
            from_dt=metrics.period.from_dt,
            to_dt=metrics.period.to_dt,
        ),
        summary=StatsSummaryResponse(
            total_tokens=metrics.total_tokens,
            turn_count=metrics.turn_count,
            session_count=metrics.session_count,
            llm_call_count=metrics.llm_call_count,
            tool_call_count=metrics.tool_call_count,
        ),
        tokens_by_day=[
            TokenDayResponse(
                date=day.date,
                total_tokens=day.total_tokens,
                prompt_tokens=day.prompt_tokens,
                completion_tokens=day.completion_tokens,
            )
            for day in metrics.tokens_by_day
        ],
        latency_ms=StatsLatencyResponse(
            turn_avg_ms=metrics.turn_latency_avg_ms,
            llm_call_avg_ms=metrics.llm_call_latency_avg_ms,
            tool_call_avg_ms=metrics.tool_call_latency_avg_ms,
        ),
        tokens=StatsTokensResponse(
            per_turn_avg=metrics.tokens_per_turn_avg,
            per_session_avg=metrics.tokens_per_session_avg,
            per_turn_spread=_spread_response(turn_spread),
            per_session_spread=_spread_response(session_spread),
        ),
        distributions=StatsDistributionsResponse(
            tokens_per_turn=[
                HistogramBucketResponse(
                    bucket_start=bucket.bucket_start,
                    bucket_end=bucket.bucket_end,
                    count=bucket.count,
                )
                for bucket in metrics.tokens_per_turn_distribution
            ],
            tokens_per_session=[
                HistogramBucketResponse(
                    bucket_start=bucket.bucket_start,
                    bucket_end=bucket.bucket_end,
                    count=bucket.count,
                )
                for bucket in metrics.tokens_per_session_distribution
            ],
        ),
    )


def _spread_response(spread) -> SpreadStatsResponse | None:
    if spread is None:
        return None
    return SpreadStatsResponse(
        min=spread.min,
        p50=spread.p50,
        p95=spread.p95,
        max=spread.max,
        count=spread.count,
    )
