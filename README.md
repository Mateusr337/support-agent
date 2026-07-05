# support-agent

## Problem

You have to develop a ChatBot that answers questions about HP documents using Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG).

You have to develop this application end-to-end, and make it available in GitHub repository.

The application has the following requirements:

- [x] Frontend with Graphical Interface, of your own choosing, to provide user interaction.
- [x] Backend must run with Python code using FastAPI.
- [x] Backend must have unit tests with at least 90% of coverage.
- [x] You can use either cloud or local (open source) models, of your own choosing. _(OpenAI wired for chat and embeddings; local models not yet supported)_
- [x] Must use an open-source Vector Database for performing RAG. _(Qdrant + `RagService` ingest and search)_
- [x] Must use only the attached documents for building the Vector Database. _(Ingest reads PDFs from `rag-docs/` only)_
- [x] Must use a Chunking Strategy to index the document on the Vector Database. _(Fixed-size chunks with overlap via `rag/chunking.py`)_
- [x] Must select a Search Strategy for retrieval. _(Query embedding + cosine similarity in Qdrant, score threshold)_
- [x] Must have support for conversation with chat history.
- [x] Must store the user chats and history in the backend.
- [x] Must run through Docker Compose, where all the application and necessary dependencies are containerized.
- [x] Scalability must be ensured with load tests — see [Load & scalability summary](#load--scalability-summary)
- [x] Must benchmark the quality of the LLM responses to the user — see [LLM quality benchmark](#llm-quality-benchmark-deepeval).

## Overview

Monorepo with a React frontend and a FastAPI backend, orchestrated via Docker Compose. PostgreSQL stores relational data; Qdrant serves as the vector database for RAG.

| Layer     | Stack                                    |
| --------- | ---------------------------------------- |
| Frontend  | React 19, TypeScript, Vite, React Router |
| Backend   | FastAPI, SQLAlchemy, Alembic, Pydantic   |
| Database  | PostgreSQL 16                            |
| Vector DB | Qdrant 1.12                              |

## Project structure

```
support-agent/
├── rag-docs/           # HP PDF corpus (indexed manually via ingest CLI)
├── backend/              # FastAPI API
├── frontend/             # React SPA (TypeScript)
├── docker-compose.yml
├── .env.example          # Docker Compose env (copy to .env)
└── .cursor/rules/        # Architecture conventions
```

Architecture details: `.cursor/rules/backend-architecture.mdc` and `.cursor/rules/frontend-architecture.mdc`.

## RAG and document corpus

HP PDFs live in **`rag-docs/`** at the repo root. They are **not** baked into the Docker image and are **not** indexed on container startup.

| Concern         | Location / mechanism                                                                                |
| --------------- | --------------------------------------------------------------------------------------------------- |
| PDF files       | `rag-docs/*.pdf` (e.g. `OMEN 17.3 inch Gaming Laptop PC.pdf`, `HP ENVY 6000 All-in-One series.pdf`) |
| Ingest CLI      | `backend/app/scripts/ingest_documents.py`                                                           |
| Ingest + search | `backend/app/rag/service.py`                                                                        |
| Chunking        | `backend/app/rag/chunking.py` (default: 1000 chars, 200 overlap)                                    |
| Embeddings      | `backend/app/rag/embeddings/` (OpenAI by default)                                                   |
| Vector storage  | `backend/app/repositories/vector_repository.py` → Qdrant                                            |
| Chat retrieval  | `SupportAgent` → `tools/search_documents` → `RagService.search()`                                   |

After adding PDFs, index manually:

```bash
# Local backend
cd backend
source .venv/bin/activate
python -m app.scripts.ingest_documents

# Or with the backend container running
docker compose exec backend python -m app.scripts.ingest_documents
```

Docker mounts `./rag-docs` read-only at `/app/rag-docs` inside the backend container (`DOCUMENTS_DIR`).

## Prerequisites

- Docker and Docker Compose
- (Optional, for local dev without Docker) Node.js 22+, Python 3.12+

## Quick start (Docker Compose)

1. Copy the root env file:

```bash
cp .env.example .env
```

2. Start all services:

```bash
docker compose up --build
```

The backend container runs `alembic upgrade head` on startup before serving the API.

3. Open:

| Service          | URL                                                                |
| ---------------- | ------------------------------------------------------------------ |
| Frontend         | [http://localhost:5173](http://localhost:5173)                     |
| Backend API      | [http://localhost:8000](http://localhost:8000)                     |
| API docs         | [http://localhost:8000/docs](http://localhost:8000/docs)           |
| Qdrant dashboard | [http://localhost:6335/dashboard](http://localhost:6335/dashboard) |

## Local development (without Docker)

Run infrastructure only with Compose, then start backend and frontend on the host:

```bash
docker compose up db qdrant
```

Compose exposes Postgres on host port **5400** (not 5432). Use that in `backend/.env` when connecting from the host.

**Backend**

```bash
cd backend
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Run `npm run typecheck` before committing frontend changes.

## Environment variables

Three env files, each for a different context:

| File                                           | Used when                          |
| ---------------------------------------------- | ---------------------------------- |
| `.env` (from `.env.example`)                   | `docker compose up` — all services |
| `backend/.env` (from `backend/.env.example`)   | Local FastAPI dev                  |
| `frontend/.env` (from `frontend/.env.example`) | Local Vite dev (`npm run dev`)     |

Root `.env` variables (required for Compose):

| Variable             | Description                                            |
| -------------------- | ------------------------------------------------------ |
| `POSTGRES_USER`      | PostgreSQL username                                    |
| `POSTGRES_PASSWORD`  | PostgreSQL password                                    |
| `POSTGRES_DB`        | PostgreSQL database name                               |
| `QDRANT_URL`         | Qdrant URL inside Docker network                       |
| `QDRANT_HTTP_PORT`   | Qdrant HTTP port on host                               |
| `QDRANT_GRPC_PORT`   | Qdrant gRPC port on host                               |
| `CORS_ORIGINS`       | Allowed frontend origins (backend)                     |
| `JWT_SECRET`         | Secret key for signing JWT access tokens               |
| `JWT_EXPIRE_MINUTES` | Access token lifetime in minutes (default: `60`)       |
| `LLM_PROVIDER`       | LLM vendor (default: `openai`)                         |
| `LLM_MODEL`          | Model name (default: `gpt-4o-mini`)                    |
| `OPENAI_API_KEY`     | OpenAI API key (required when provider is openai)      |
| `EMBEDDING_PROVIDER` | Embedding vendor for RAG (default: `openai`)           |
| `EMBEDDING_MODEL`    | Embedding model (default: `text-embedding-3-small`)    |
| `QDRANT_COLLECTION`  | Qdrant collection name for document vectors            |
| `DOCUMENTS_DIR`      | Folder with HP PDFs (Compose default: `/app/rag-docs`) |
| `VITE_API_URL`       | Backend URL exposed to the browser                     |

`backend/.env` uses the same JWT and LLM variables. When using Compose for `db` and `qdrant` only, set `DATABASE_URL` to port **5400** (see `backend/.env.example`).

## API

All endpoints require a valid JWT (`Authorization: Bearer <token>`) except register and login.

### Auth

| Method | Endpoint             | Description                                        |
| ------ | -------------------- | -------------------------------------------------- |
| `POST` | `/api/v1/users`      | Register a new user (`201`, `409` if email exists) |
| `POST` | `/api/v1/auth/login` | Login (`200` + JWT, `401` on invalid credentials)  |
| `GET`  | `/api/v1/auth/me`    | Current user from JWT (`401` if token invalid)     |

### Chat

| Method | Endpoint                                           | Description                                                                    |
| ------ | -------------------------------------------------- | ------------------------------------------------------------------------------ |
| `POST` | `/api/v1/chat/conversations`                       | Create a new chat session (`201`)                                              |
| `GET`  | `/api/v1/chat/conversations/active`                | Get or create the user's active session (`200`)                                |
| `POST` | `/api/v1/chat/conversations/reload`                | Finalize the active session and create a new one (`201`)                       |
| `GET`  | `/api/v1/chat/conversations/{session_id}/messages` | List messages, cursor-paginated (`limit`, `offset`; default `10`)              |
| `POST` | `/api/v1/chat/conversations/{session_id}/messages` | Send a message (`200` SSE stream; RAG + LLM assistant reply with chat history) |

### Audit

| Method | Endpoint             | Description                                                                                           |
| ------ | -------------------- | ----------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/audit/logs` | List audit logs, cursor-paginated (`limit`, `offset`; default `25`; filters: `session_id`, `turn_id`) |

### Stats

| Method | Endpoint               | Description                                                                                    |
| ------ | ---------------------- | ---------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/stats/metrics` | Aggregated usage/latency metrics for the logged-in user (`period=today\|week`; optional filters) |

See [`specs-docs/stats-dashboard.md`](specs-docs/stats-dashboard.md) for metric definitions and audit-log mapping.

Assistant replies use the support agent with document search (`search_documents`) and OpenAI chat completion. Pipeline steps are recorded in audit logs.

#### Send message (SSE)

`POST /api/v1/chat/conversations/{session_id}/messages` returns `text/event-stream` with JSON events:

| Event          | Payload                                           |
| -------------- | ------------------------------------------------- |
| `turn_started` | `{ "turn_id": "..." }`                            |
| `tool_call`    | `{ "name": "search_documents" }`                  |
| `token`        | `{ "content": "..." }`                            |
| `done`         | `{ "assistant_message_id": 1, "content": "..." }` |
| `error`        | `{ "message": "..." }`                            |

The client shows the user message optimistically; the server does not echo it in the stream.

See [`docs/chat-sse-streaming.md`](docs/chat-sse-streaming.md) for the full SSE contract, flow, and extension guide.

### Health

| Method | Endpoint                | Description      |
| ------ | ----------------------- | ---------------- |
| `GET`  | `/api/v1/health`        | API liveness     |
| `GET`  | `/api/v1/health/db`     | PostgreSQL check |
| `GET`  | `/api/v1/health/qdrant` | Qdrant check     |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Frontend routes

| Path        | Page          | Access        |
| ----------- | ------------- | ------------- |
| `/`         | redirect      | public        |
| `/login`    | LoginPage     | guest only    |
| `/register` | RegisterPage  | guest only    |
| `/chat`     | ChatPage      | authenticated |
| `/stats`    | StatsPage     | authenticated |
| `/audit`    | AuditLogsPage | authenticated |

The chat UI loads the latest messages first and fetches older messages when scrolling to the top. The audit logs page uses the same cursor-pagination pattern (default 25 logs per page, infinite scroll).

## Backend tests

Tests use **pytest**, **pytest-cov**, and **httpx** (`backend/requirements-dev.txt`). They run on the host, not inside the backend container (the Docker image installs only `requirements.txt`).

Tests use an in-memory SQLite database (no Postgres required). Override `get_db` via `app.dependency_overrides` in `conftest.py`.

Current coverage: **97.1%** on `app/` (**180 tests**, threshold 95%).

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                              # run all tests
pytest --cov=app --cov-report=term-missing   # with coverage %
pytest --cov=app --cov-report=html           # HTML report → htmlcov/index.html
```

Layout mirrors the backend layers — see `.cursor/rules/backend-architecture.mdc` (Testing section).

LLM response quality is benchmarked separately — see [LLM quality benchmark](#llm-quality-benchmark-deepeval).

## LLM quality benchmark (DeepEval)

Not part of `pytest` or coverage. Requires the live API, ingested PDFs, and `OPENAI_API_KEY`.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.scripts.run_deepeval --base-url http://localhost:8000
```

Latest report: [backend/eval_report.json](backend/eval_report.json). Case specs: [specs-docs/agent-manual-tests.md](specs-docs/agent-manual-tests.md).

| Case                  | Answer Relevancy | Faithfulness | Contextual Relevancy / Hallucination | GEval            | Pass |
| --------------------- | ---------------- | ------------ | ------------------------------------ | ---------------- | ---- |
| 1 - Laptop safety     | 1.00             | 1.00         | Contextual 0.60                      | SafetyFacts 1.00 | Yes  |
| 10 - No hallucination | 0.75             | 1.00         | Hallucination 0.00                   | NoPrinthead 1.00 | Yes  |

**2/2** cases passed (2026-07-04).

## Current status

Implemented:

- Docker Compose with PostgreSQL, Qdrant, backend, and frontend
- Alembic migrations (users, chat sessions, chat messages, audit logs)
- Health endpoints: `/api/v1/health`, `/api/v1/health/db`, `/api/v1/health/qdrant`
- Auth: register, login, JWT, `/api/v1/auth/me`
- Chat API: sessions, message storage, cursor pagination, LLM assistant replies with chat history
- RAG pipeline: PDF ingest CLI, chunking, OpenAI embeddings, Qdrant vector search
- Support agent: `search_documents` tool wired to `RagService` on every user message
- Audit logging: backend pipeline events (agent, LLM, tools) + `/api/v1/audit/logs` API
- Frontend: auth (login / register), chat UI with scroll-to-load-older messages, audit logs UI with infinite scroll
- LLM integration: `core/llm/` adapters and `SupportAgent` wired into `ChatService`
- Backend test suite: **180 tests**, **97.1%** coverage on `app/`
- [LLM quality benchmark](#llm-quality-benchmark-deepeval)
- Load tests (Locust Mode A): **300 users, 0% errors**, ~147 req/s — [summary](#load--scalability-summary)

Not yet implemented:

- Full 10-case DeepEval suite (cases 2–9)
- Production ingest pipeline, admin UI, guardrails — [scaling-to-production.md](specs-docs/scaling-to-production.md)

Manual step before RAG answers work: place HP PDFs in `rag-docs/` and run the ingest CLI (see [RAG and document corpus](#rag-and-document-corpus)).

For scaling to production (roadmap, ingest pipeline, guardrails, orchestration): [specs-docs/scaling-to-production.md](specs-docs/scaling-to-production.md).

## Load & scalability summary

Locust **Mode A** (`LOAD_TEST=true`, fake agent — no OpenAI cost) validates API/DB/SSE throughput. Methodology and analysis: [specs-docs/locust-stress-test-methodology.md](specs-docs/locust-stress-test-methodology.md).

| Scenario | Config | Failures | Throughput |
| -------- | ------ | -------- | ------------ |
| Load — 10 users, 30 s | 1 worker, default pool | 0% | — |
| Stress — 300 users | 1 worker, default pool | **~37%** | DB pool exhausted |
| Stress — 300 users | 4 workers, tuned pool, `LOAD_TEST=true` | **0%** | **~147 req/s** (~8.8k req/min) |

**Fixes applied:** SQLAlchemy pool tuning, `UVICORN_WORKERS=4`, audit log batching (no per-entry flush), `FakeSupportAgent` for isolated infra tests.

Mode B (real OpenAI + RAG) was not stress-tested to avoid API cost; the same Locust harness supports it for future provider SLA tests.

## Load testing (Locust)

Load tests live in `load/` and run **against a running API** (Docker Compose or local uvicorn). They are separate from `backend/tests/`.

### Setup

```bash
python -m venv load/.venv
source load/.venv/bin/activate
pip install -r load/requirements.txt
```

### Mode A — API infra (no OpenAI)

Tests login, one fake chat turn (seeds audit logs), and paginated audit log reads.

**Quick path:** `./load/run_locust.sh` starts the backend with 4 workers + tuned pool + fake agent, then runs Locust:

```bash
source load/.venv/bin/activate   # after pip install -r load/requirements.txt
./load/run_locust.sh --headless -u 50 -r 5 -t 5m
```

**Manual path:**

1. Enable the fake agent on the backend:

   ```bash
   # In .env at repo root
   LOAD_TEST=true
   ```

2. Restart the backend (optionally with load overrides):

   ```bash
   LOAD_TEST=true UVICORN_WORKERS=4 docker compose up -d --build backend
   ```

3. Run Locust:

   ```bash
   locust -f load/locustfile.py --host http://localhost:8000
   ```

   Headless example (50 users, 5 min):

   ```bash
   locust -f load/locustfile.py --host http://localhost:8000 \
     --headless -u 50 -r 5 -t 5m
   ```

   Mode is selected via `LOAD_MODE` env var (default `A`). Do not pass `--tags`.

Full stress-test process: [specs-docs/locust-stress-test-methodology.md](specs-docs/locust-stress-test-methodology.md). Production roadmap: [specs-docs/scaling-to-production.md](specs-docs/scaling-to-production.md).

### Mode B — real agent (OpenAI + RAG)

Tests full chat SSE turns with latency metrics (`turn_complete`, `time_to_first_token`).

1. Ensure `LOAD_TEST=false` and `OPENAI_API_KEY` is set in `.env`.
2. Ingest PDFs: `docker compose exec backend python -m app.scripts.ingest_documents`
3. Run Locust (start with few users — each turn calls OpenAI):

   ```bash
   LOAD_MODE=B locust -f load/locustfile.py --host http://localhost:8000 \
     --headless -u 5 -r 1 -t 5m
   ```

   Not run in this project (OpenAI cost). Use for provider SLA checks with low user count when needed.

### Results and conclusions

Mode A (`LOAD_TEST=true`, fake agent) isolates API/DB/SSE limits without OpenAI cost. After tuning, the stack sustained **300 concurrent virtual users** for 5 minutes with **0% failures**.

| Metric | Before fixes | After fixes |
| ------ | ------------ | ----------- |
| Config | 1 worker, default pool (~15 connections) | 4 workers, `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20` |
| Failures at 300 users | **~37%** (`QueuePool limit` in logs) | **0%** |
| Throughput | DB pool exhausted | **~147 req/s** (~8.8k req/min), 26k+ requests |

**Latency at 300 users (after fixes):**

| Endpoint | Median | p95 |
| -------- | ------ | --- |
| `GET /audit/logs` | ~3 ms | ~8 ms |
| `GET /stats/metrics` | ~5 ms | ~15 ms |
| `POST /auth/login [repeat]` | ~190 ms | ~220 ms |
| `POST /users [register]` | ~340 ms | ~730 ms |

**Conclusions**

- The main bottleneck under stress was **Postgres connection pooling**, not CPU or Locust itself — fixed by worker count + pool sizing + audit batching (no per-entry flush).
- Mode A validates **platform** scalability (auth, SSE, audit, stats). Mode B (real OpenAI + RAG) was not stress-tested to avoid API cost; throughput there is **provider-bound**.
- Capacity planning: `peak_db_connections ≈ UVICORN_WORKERS × (DB_POOL_SIZE + DB_MAX_OVERFLOW)` — e.g. 4 × 30 = **120** checkouts with current tuning.
- Pass gate for future runs: **< 1% failures** at target user count; re-run with `./load/run_locust.sh --headless -u 300 -r 30 -t 5m` after infra changes.

Full methodology and troubleshooting: [specs-docs/locust-stress-test-methodology.md](specs-docs/locust-stress-test-methodology.md).
