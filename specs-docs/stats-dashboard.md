# Stats dashboard

Usage and latency metrics derived from audit logs for the authenticated user.

## API

`GET /api/v1/stats/metrics`

| Query param   | Values              | Default |
|---------------|---------------------|---------|
| `period`      | `today`, `week`     | `today` |
| `from` / `to` | ISO datetime        | —       |
| `session_id`  | UUID                | —       |
| `turn_id`     | UUID                | —       |

**Week** = rolling last 7 calendar days (today + 6 prior days), UTC.

## Metric sources (audit log)

| Metric | Audit filter |
|--------|----------------|
| Tokens by day | `type = "Token Usage"` → `data.total_tokens`, grouped by `created_at` date |
| Avg tokens / turn | Sum tokens per `turn_id`, then average |
| Avg tokens / session | Sum tokens per `session_id`, then average |
| Spread (min, p50, p95, max) | Same per-turn / per-session totals |
| Avg LLM call latency | `type = "Agent"`, `message IN ("LLM response", "LLM stream response")`, `data.latency_ms` |
| Avg tool call latency | `type = "Tool Result"`, `data.latency_ms` |
| Avg turn latency | `message = "Agent reply generated"`, `data.latency_ms` |

Turn latency is recorded at the end of `ChatService.process_message_stream`.

## Frontend

| Path | Page |
|------|------|
| `/stats` | StatsPage (authenticated) |

- **Today / Week** toggle refetches in the background.
- **Refresh** updates data without full-page loading after the first load.
- CSS bar charts (no chart library).

## Manual test

1. `docker compose up --build`
2. Log in, send a few chat messages (Mode B or real agent for token usage).
3. Open **Stats** from the header menu.
4. Confirm KPIs, tokens-by-day chart, spread panels, and histograms update after **Refresh**.

## Load test

Mode A seeds audit logs via fake chat; Locust calls:

- `GET /api/v1/stats/metrics?period=today`
- `GET /api/v1/stats/metrics?period=week`

See [locust-stress-test-methodology.md](locust-stress-test-methodology.md).
