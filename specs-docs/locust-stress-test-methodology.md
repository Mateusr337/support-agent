# Locust stress test methodology

How we used Locust to find limits, improve throughput, and analyze this API. The same process applies to **Mode B** (real OpenAI) or another LLM provider when budget allows.

Related: [README — Load testing](../README.md#load-testing-locust) · [Scaling to production](scaling-to-production.md)

## Goal

Answer the project requirement: **how many requests per minute the solution supports**, with evidence (failure rate, latency, RPS).

We split infra stress from LLM stress:

| Mode  | `LOAD_MODE`   | Backend                       | Measures                                             |
| ----- | ------------- | ----------------------------- | ---------------------------------------------------- |
| **A** | `A` (default) | `LOAD_TEST=true` → fake agent | API, Postgres, SSE, auth, audit — **no OpenAI cost** |
| **B** | `B`           | `LOAD_TEST=false` + API key   | Full chat + RAG + OpenAI — use sparingly             |

Mode A is the primary scalability proof. Mode B reuses the same harness when you need real turn latency (TTFT, turn_complete).

## Discovery process (what we did)

### 1. Baseline load test

Small, steady traffic to confirm the harness works:

```bash
LOAD_TEST=true UVICORN_WORKERS=1 docker compose up -d --build backend
locust -f load/locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 -t 30s
```

**Result:** 0% errors — login, SSE seed, audit reads all green.

### 2. Stress test (find breaking point)

High user count and spawn rate without pool/worker tuning:

```bash
# 1 worker, default pool (~15 connections)
locust -f load/locustfile.py --host http://localhost:8000 --headless -u 300 -r 30 -t 3m
```

**Result:** ~**37% failures**. Backend logs showed:

```text
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached
```

**Root cause:** Single uvicorn worker + small SQLAlchemy pool. Each virtual user runs heavy `on_start` (register, login, active session, SSE seed) and holds DB connections during SSE.

### 3. Fixes applied

| Change           | File / config                                            | Effect                                |
| ---------------- | -------------------------------------------------------- | ------------------------------------- |
| Pool tuning      | `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`, `pool_pre_ping` | More connections per worker           |
| Multiple workers | `UVICORN_WORKERS=4` in `.env`                            | More processes + pools; no `--reload` |
| Fake agent       | `LOAD_TEST=true`, `FakeSupportAgent`                     | Mode A without OpenAI                 |
| Audit batching   | Remove per-entry `flush()`                               | Fewer DB round-trips per turn         |
| Locust errors    | `catch_response`, `StopUser`                             | Clean failure stats under load        |

Formula for capacity planning:

```text
peak_db_connections ≈ UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

Example: 4 × (10 + 20) = **120** possible checkouts.

### 4. Re-test after fixes

```bash
LOAD_TEST=true UVICORN_WORKERS=4 docker compose up --build -d backend
locust -f load/locustfile.py --host http://localhost:8000 --headless -u 300 -r 30 -t 5m
```

**Result:** **0% failures**, ~**147 req/s** aggregate (~8,800 req/min), 26k+ requests in one run.

| Endpoint (300 users)        | Median  | p95     | Notes                  |
| --------------------------- | ------- | ------- | ---------------------- |
| `GET /audit/logs`           | ~3 ms   | ~8 ms   | Main task traffic      |
| `GET /stats/metrics`        | ~5 ms   | ~15 ms  | Aggregated audit query |
| `POST /auth/login [repeat]` | ~190 ms | ~220 ms | Stable                 |
| `POST /users [register]`    | ~340 ms | ~730 ms | Once per user at start |

## How to analyze the app during a run

### Locust UI / report

- **Failures %** — primary pass/fail gate (< 1% for “supported load”)
- **RPS** — requests per second (× 60 = RPM)
- **p50 / p95 / p99** per endpoint — find slow paths
- **# Requests** on `register` / `seed SSE` vs `audit/logs` — confirms workload mix

Save HTML report: add `--html report.html` to headless runs.

### Backend

```bash
docker compose logs backend --tail 100    # pool timeouts, tracebacks
docker stats                                 # CPU / memory per container
```

### Postgres (optional)

```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'support_agent';
```

If active connections ≈ `workers × (pool_size + overflow)` under stress, pool sizing is the lever.

## Improving requests per minute (checklist)

Use in order; re-run Mode A after each change:

1. **Increase `UVICORN_WORKERS`** — more parallel request handling (watch Postgres `max_connections`).
2. **Tune `DB_POOL_SIZE` / `DB_MAX_OVERFLOW`** — match worker count; avoid exceeding Postgres limits.
3. **Locust client `--processes N`** — if Locust CPU saturates before the API.
4. **Reduce work per user in `on_start`** — optional pre-seeded users if register/login is not the test focus.
5. **Step ramp** — 50 → 100 → 150 → 300 (3 min each) instead of jumping straight to 300.
6. **Cap LLM history / async I/O** — see [scaling-to-production.md](scaling-to-production.md) for chat-path improvements.

## Running Mode B (OpenAI or another provider)

Same steps; different cost profile:

1. `LOAD_TEST=false`, set provider API key, ingest PDFs.
2. Start with **3–5 users**, low spawn rate — each turn calls embeddings + chat.
3. Record custom metrics: `turn_complete`, `time_to_first_token` (already in `locustfile.py`).
4. Compare p95 TTFT and max concurrent users; bottleneck will shift to **provider rate limits**, not Postgres.

To test a non-OpenAI provider: wire the adapter in `backend/app/core/llm/` and run Mode B unchanged — Locust only hits HTTP.

## Recommended protocol for reviewers

1. Show **before** (300 users, ~37% errors, pool timeout in logs).
2. Show **fixes** (table above).
3. Show **after** (300 users, 0% errors, ~147 RPS screenshot).
4. State scope: Mode A validates **platform** scalability; Mode B optional for **LLM** SLA when budget allows.

Update the summary table in [README](../README.md#load--scalability-summary) after each benchmark run.
