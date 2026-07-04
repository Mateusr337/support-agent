from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import mean
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.audit_log_repository import AuditLogRepository
from app.services.stats_constants import (
    LLM_LATENCY_MESSAGES,
    TOKEN_HISTOGRAM_BUCKETS,
    TOKEN_USAGE_TYPE,
    TOOL_RESULT_TYPE,
    TURN_LATENCY_MESSAGE,
)


class InvalidStatsPeriodError(ValueError):
    pass


@dataclass(frozen=True)
class StatsPeriodRange:
    preset: str | None
    from_dt: datetime
    to_dt: datetime


@dataclass(frozen=True)
class TokenDayBucket:
    date: date
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


@dataclass(frozen=True)
class SpreadStats:
    min: int
    p50: int
    p95: int
    max: int
    count: int


@dataclass(frozen=True)
class HistogramBucket:
    bucket_start: int
    bucket_end: int | None
    count: int


@dataclass(frozen=True)
class StatsMetrics:
    period: StatsPeriodRange
    total_tokens: int
    turn_count: int
    session_count: int
    llm_call_count: int
    tool_call_count: int
    tokens_by_day: list[TokenDayBucket]
    turn_latency_avg_ms: int | None
    llm_call_latency_avg_ms: int | None
    tool_call_latency_avg_ms: int | None
    tokens_per_turn_avg: float | None
    tokens_per_session_avg: float | None
    tokens_per_turn_spread: SpreadStats | None
    tokens_per_session_spread: SpreadStats | None
    tokens_per_turn_distribution: list[HistogramBucket]
    tokens_per_session_distribution: list[HistogramBucket]


class StatsService:
    def __init__(self, db: Session) -> None:
        self._repository = AuditLogRepository(db)

    def get_metrics(
        self,
        *,
        user_id: int,
        period: str = "today",
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        session_id: UUID | None = None,
        turn_id: UUID | None = None,
    ) -> StatsMetrics:
        period_range = resolve_period(period=period, from_dt=from_dt, to_dt=to_dt)
        logs = self._repository.list_for_metrics(
            user_id=user_id,
            from_dt=period_range.from_dt,
            to_dt=period_range.to_dt,
            session_id=session_id,
            turn_id=turn_id,
        )
        return build_metrics(logs, period_range)


def resolve_period(
    *,
    period: str,
    from_dt: datetime | None,
    to_dt: datetime | None,
) -> StatsPeriodRange:
    now = datetime.now(UTC)

    if from_dt is not None and to_dt is not None:
        start = _ensure_utc(from_dt)
        end = _ensure_utc(to_dt)
        if start > end:
            raise InvalidStatsPeriodError("'from' must be before or equal to 'to'")
        return StatsPeriodRange(preset=None, from_dt=start, to_dt=end)

    if period == "today":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return StatsPeriodRange(preset="today", from_dt=start, to_dt=now)

    if period == "week":
        start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
        return StatsPeriodRange(preset="week", from_dt=start, to_dt=now)

    raise InvalidStatsPeriodError("period must be 'today' or 'week'")


def build_metrics(logs: list, period_range: StatsPeriodRange) -> StatsMetrics:
    tokens_by_day: dict[date, dict[str, int]] = {}
    tokens_by_turn: dict[UUID, int] = {}
    tokens_by_session: dict[UUID, int] = {}
    llm_latencies: list[int] = []
    tool_latencies: list[int] = []
    turn_latencies: list[int] = []
    llm_call_count = 0
    tool_call_count = 0

    for log in logs:
        data = log.data or {}
        log_date = _log_date(log.created_at)

        if log.type == TOKEN_USAGE_TYPE:
            prompt = int(data.get("prompt_tokens") or 0)
            completion = int(data.get("completion_tokens") or 0)
            total = int(data.get("total_tokens") or prompt + completion)

            day_bucket = tokens_by_day.setdefault(
                log_date,
                {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            day_bucket["prompt_tokens"] += prompt
            day_bucket["completion_tokens"] += completion
            day_bucket["total_tokens"] += total

            tokens_by_turn[log.turn_id] = tokens_by_turn.get(log.turn_id, 0) + total
            tokens_by_session[log.session_id] = tokens_by_session.get(log.session_id, 0) + total
            continue

        latency_ms = data.get("latency_ms")
        if latency_ms is None:
            continue

        latency = int(latency_ms)

        if log.type == TOOL_RESULT_TYPE:
            tool_latencies.append(latency)
            tool_call_count += 1
            continue

        if log.message in LLM_LATENCY_MESSAGES:
            llm_latencies.append(latency)
            llm_call_count += 1
            continue

        if log.message == TURN_LATENCY_MESSAGE:
            turn_latencies.append(latency)

    turn_totals = list(tokens_by_turn.values())
    session_totals = list(tokens_by_session.values())
    total_tokens = sum(turn_totals)

    tokens_by_day_list = [
        TokenDayBucket(
            date=day,
            total_tokens=values["total_tokens"],
            prompt_tokens=values["prompt_tokens"],
            completion_tokens=values["completion_tokens"],
        )
        for day, values in sorted(tokens_by_day.items())
    ]

    return StatsMetrics(
        period=period_range,
        total_tokens=total_tokens,
        turn_count=len(tokens_by_turn),
        session_count=len(tokens_by_session),
        llm_call_count=llm_call_count,
        tool_call_count=tool_call_count,
        tokens_by_day=tokens_by_day_list,
        turn_latency_avg_ms=_avg_int(turn_latencies),
        llm_call_latency_avg_ms=_avg_int(llm_latencies),
        tool_call_latency_avg_ms=_avg_int(tool_latencies),
        tokens_per_turn_avg=_avg_float(turn_totals),
        tokens_per_session_avg=_avg_float(session_totals),
        tokens_per_turn_spread=_spread(turn_totals),
        tokens_per_session_spread=_spread(session_totals),
        tokens_per_turn_distribution=_histogram(turn_totals),
        tokens_per_session_distribution=_histogram(session_totals),
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _log_date(value: datetime) -> date:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(UTC).date()


def _avg_int(values: list[int]) -> int | None:
    if not values:
        return None
    return round(mean(values))


def _avg_float(values: list[int]) -> float | None:
    if not values:
        return None
    return round(mean(values), 1)


def _percentile(values: list[int], percentile: float) -> int:
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    index = (len(sorted_values) - 1) * (percentile / 100)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = index - lower
    return round(sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight)


def _spread(values: list[int]) -> SpreadStats | None:
    if not values:
        return None
    return SpreadStats(
        min=min(values),
        p50=_percentile(values, 50),
        p95=_percentile(values, 95),
        max=max(values),
        count=len(values),
    )


def _histogram(values: list[int]) -> list[HistogramBucket]:
    counts = [0] * len(TOKEN_HISTOGRAM_BUCKETS)
    for value in values:
        for index, (start, end) in enumerate(TOKEN_HISTOGRAM_BUCKETS):
            if value >= start and (end is None or value < end):
                counts[index] += 1
                break

    return [
        HistogramBucket(bucket_start=start, bucket_end=end, count=counts[index])
        for index, (start, end) in enumerate(TOKEN_HISTOGRAM_BUCKETS)
    ]
