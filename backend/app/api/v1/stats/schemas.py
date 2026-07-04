from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class StatsPeriodResponse(BaseModel):
    preset: str | None
    from_dt: datetime = Field(serialization_alias="from")
    to_dt: datetime = Field(serialization_alias="to")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TokenDayResponse(BaseModel):
    date: date
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


class SpreadStatsResponse(BaseModel):
    min: int
    p50: int
    p95: int
    max: int
    count: int


class HistogramBucketResponse(BaseModel):
    bucket_start: int
    bucket_end: int | None
    count: int


class StatsSummaryResponse(BaseModel):
    total_tokens: int
    turn_count: int
    session_count: int
    llm_call_count: int
    tool_call_count: int


class StatsLatencyResponse(BaseModel):
    turn_avg_ms: int | None
    llm_call_avg_ms: int | None
    tool_call_avg_ms: int | None


class StatsTokensResponse(BaseModel):
    per_turn_avg: float | None
    per_session_avg: float | None
    per_turn_spread: SpreadStatsResponse | None
    per_session_spread: SpreadStatsResponse | None


class StatsDistributionsResponse(BaseModel):
    tokens_per_turn: list[HistogramBucketResponse]
    tokens_per_session: list[HistogramBucketResponse]


class StatsMetricsResponse(BaseModel):
    period: StatsPeriodResponse
    summary: StatsSummaryResponse
    tokens_by_day: list[TokenDayResponse]
    latency_ms: StatsLatencyResponse
    tokens: StatsTokensResponse
    distributions: StatsDistributionsResponse
