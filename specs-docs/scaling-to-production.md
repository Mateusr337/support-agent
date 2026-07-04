# Scaling to production

Path from the current Docker Compose dev setup to a production-ready deployment.

Related: [Locust stress test methodology](locust-stress-test-methodology.md) · [Load testing (README)](../README.md#load-testing-locust)

## Stress test discovery (summary)

We used Locust **Mode A** (`LOAD_TEST=true`, fake agent) to isolate API/DB limits without OpenAI cost. Full write-up: [locust-stress-test-methodology.md](locust-stress-test-methodology.md).

| Step | Config | Outcome |
| ---- | ------ | ------- |
| Load (10 users) | 1 worker, default pool | 0% errors |
| Stress (300 users) | 1 worker, default pool | **~37% errors** — `QueuePool` exhausted |
| Fix | Pool tuning + `UVICORN_WORKERS=4` + audit batching | — |
| Re-stress (300 users) | 4 workers, tuned pool | **0% errors**, ~**147 req/s** (~8.8k req/min) |

The same Locust harness supports **Mode B** (real LLM/RAG) when you need provider-level stress tests — start with few users; cost and rate limits dominate. See methodology doc.

## Where limits show up today

| Layer | Main constraint |
| ----- | --------------- |
| OpenAI | Latency and rate limits per chat turn (Mode B) |
| API | Tuned: 4 workers; dev default was 1 worker + `--reload` |
| Postgres | Pool per worker; SSE holds a DB session for the full turn |
| Event loop | Sync DB and Qdrant calls inside async handlers |
| Chat | Full session history sent to the LLM every turn |
| Ingest | Offline CLI only — no admin UI or async pipeline |

With current tuning, **Mode A supports 300 concurrent virtual users at 0% errors** on local Docker Compose. Real chat throughput (Mode B) remains lower and provider-bound.

## Checklist

**Done**

- SQLAlchemy pool tuning (`backend/app/core/database.py`)
- Multiple uvicorn workers via `UVICORN_WORKERS`
- Audit logs: no per-entry `flush()`
- Locust Mode A stress validated (300 users, 0% failures)
- Locust methodology documented

**Next (high impact)**

- [ ] Reverse proxy (TLS, SSE: `proxy_buffering off`) + static frontend build
- [ ] Size Postgres `max_connections` ≥ `UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)` + headroom
- [ ] Cap LLM chat history (last N messages or token window)
- [ ] Offload sync DB/Qdrant I/O: `asyncio.to_thread(...)` in async paths

**Ingestion & document management**

- [ ] Structured **ingestion logs** (job id, file, chunks, duration, errors) for ops visibility
- [ ] **Admin UI** to upload PDFs (new frontend or admin section) — replace manual `rag-docs/` + CLI
- [ ] **Async ingest pipeline:** backend receives upload → **S3** (or object storage) → **Kafka** event → dedicated **indexer service** embeds and writes **Qdrant** → completion event (or webhook) back to API/admin UI

**Agent & RAG quality**

- [ ] **Input guardrails agent** — validate/sanitize user message before main agent
- [ ] **Output guardrails agent** — validate response (safety, faithfulness signals); retry or refuse on failure
- [ ] **Tool strategy:** per document-type tools, or single `search_documents` with filter args (product category, model) to reduce cross-corpora leakage
- [ ] **Intent orchestration** — router agent delegates to specialized agents by topic/product line (when catalog and requirements grow)

**Later**

- [ ] Rate limiting on chat endpoints
- [ ] Structured logs and metrics (SSE duration, pool wait, OpenAI errors)
- [ ] Secrets via env / secret manager
- [ ] Mode B load test with OpenAI or alternate provider (small user count, budgeted)

## Rollout order

1. Workers + reverse proxy + static frontend *(workers done)*
2. Postgres `max_connections` aligned with pool × workers
3. Async ingestion pipeline + admin upload UI
4. Guardrails + tool/orchestration improvements (demand-driven)
5. Cap chat history + async I/O offload
6. Mode B spot checks; observability and rate limits as needed

## Workers (quick reference)

```text
peak_db_connections ≈ UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

Stress config used: `LOAD_TEST=true UVICORN_WORKERS=4` in `.env`, `docker compose up --build -d backend`.

## Horizontal scaling

API is stateless (JWT). Multiple replicas behind a load balancer share PostgreSQL and Qdrant. Use **sticky sessions** for SSE. Ingest/indexer and Kafka consumers scale independently of chat API.

## Load test results

| Scenario | Config | Result |
| -------- | ------ | ------ |
| Mode A — 10 users, 30 s | 1 worker, default pool | **Pass** (0% errors) |
| Mode A — 300 users | 1 worker, default pool | **~37% errors** (pool exhausted) |
| Mode A — 300 users | 4 workers, tuned pool, `LOAD_TEST=true` | **Pass** (0% errors, ~147 req/s) |
| Mode B — real LLM stress | Not run | Skipped — OpenAI cost; harness ready |

Detailed analysis: [locust-stress-test-methodology.md](locust-stress-test-methodology.md).
