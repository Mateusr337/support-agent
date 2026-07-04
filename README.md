# support-agent

## Problem

You have to develop a ChatBot that answers questions about HP documents using Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG).

You have to develop this application end-to-end, and make it available in GitHub repository.

The application has the following requirements:

- [x] Frontend with Graphical Interface, of your own choosing, to provide user interaction.
- [x] Backend must run with Python code using FastAPI.
- [x] Backend must have unit tests with at least 90% of coverage.
- [x] You can use either cloud or local (open source) models, of your own choosing. *(OpenAI wired for chat and embeddings; local models not yet supported)*
- [x] Must use an open-source Vector Database for performing RAG. *(Qdrant + `RagService` ingest and search)*
- [x] Must use only the attached documents for building the Vector Database. *(Ingest reads PDFs from `rag-docs/` only)*
- [x] Must use a Chunking Strategy to index the document on the Vector Database. *(Fixed-size chunks with overlap via `rag/chunking.py`)*
- [x] Must select a Search Strategy for retrieval. *(Query embedding + cosine similarity in Qdrant, score threshold)*
- [x] Must have support for conversation with chat history.
- [x] Must store the user chats and history in the backend.
- [x] Must run through Docker Compose, where all the application and necessary dependencies are containerized.
- [ ] Scalability must be ensured with load tests (how many requests per minute the solution supports)
- [x] Must benchmark the quality of the LLM responses to the user.

## Overview

Monorepo with a React frontend and a FastAPI backend, orchestrated via Docker Compose. PostgreSQL stores relational data; Qdrant serves as the vector database for RAG.

| Layer     | Stack                                      |
| --------- | ------------------------------------------ |
| Frontend  | React 19, TypeScript, Vite, React Router   |
| Backend   | FastAPI, SQLAlchemy, Alembic, Pydantic     |
| Database  | PostgreSQL 16                              |
| Vector DB | Qdrant 1.12                                |

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

| Concern | Location / mechanism |
| ------- | -------------------- |
| PDF files | `rag-docs/*.pdf` (e.g. `OMEN 17.3 inch Gaming Laptop PC.pdf`, `HP ENVY 6000 All-in-One series.pdf`) |
| Ingest CLI | `backend/app/scripts/ingest_documents.py` |
| Ingest + search | `backend/app/rag/service.py` |
| Chunking | `backend/app/rag/chunking.py` (default: 1000 chars, 200 overlap) |
| Embeddings | `backend/app/rag/embeddings/` (OpenAI by default) |
| Vector storage | `backend/app/repositories/vector_repository.py` → Qdrant |
| Chat retrieval | `SupportAgent` → `tools/search_documents` → `RagService.search()` |

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

| Variable             | Description                                      |
| -------------------- | ------------------------------------------------ |
| `POSTGRES_USER`      | PostgreSQL username                              |
| `POSTGRES_PASSWORD`  | PostgreSQL password                              |
| `POSTGRES_DB`        | PostgreSQL database name                         |
| `QDRANT_URL`         | Qdrant URL inside Docker network                 |
| `QDRANT_HTTP_PORT`   | Qdrant HTTP port on host                         |
| `QDRANT_GRPC_PORT`   | Qdrant gRPC port on host                         |
| `CORS_ORIGINS`       | Allowed frontend origins (backend)               |
| `JWT_SECRET`         | Secret key for signing JWT access tokens         |
| `JWT_EXPIRE_MINUTES` | Access token lifetime in minutes (default: `60`) |
| `LLM_PROVIDER`       | LLM vendor (default: `openai`)                   |
| `LLM_MODEL`          | Model name (default: `gpt-4o-mini`)              |
| `OPENAI_API_KEY`     | OpenAI API key (required when provider is openai) |
| `EMBEDDING_PROVIDER` | Embedding vendor for RAG (default: `openai`)       |
| `EMBEDDING_MODEL`    | Embedding model (default: `text-embedding-3-small`) |
| `QDRANT_COLLECTION`  | Qdrant collection name for document vectors        |
| `DOCUMENTS_DIR`      | Folder with HP PDFs (Compose default: `/app/rag-docs`) |
| `VITE_API_URL`       | Backend URL exposed to the browser               |

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

| Method | Endpoint                                          | Description                                              |
| ------ | ------------------------------------------------- | -------------------------------------------------------- |
| `POST` | `/api/v1/chat/conversations`                      | Create a new chat session (`201`)                        |
| `GET`  | `/api/v1/chat/conversations/active`               | Get or create the user's active session (`200`)          |
| `POST` | `/api/v1/chat/conversations/reload`               | Finalize the active session and create a new one (`201`) |
| `GET`  | `/api/v1/chat/conversations/{session_id}/messages` | List messages, cursor-paginated (`limit`, `offset`; default `10`) |
| `POST` | `/api/v1/chat/conversations/{session_id}/messages` | Send a message (`200` SSE stream; RAG + LLM assistant reply with chat history) |

### Audit

| Method | Endpoint              | Description                                                       |
| ------ | --------------------- | ----------------------------------------------------------------- |
| `GET`  | `/api/v1/audit/logs`  | List audit logs, cursor-paginated (`limit`, `offset`; default `25`; filters: `session_id`, `turn_id`) |

Assistant replies use the support agent with document search (`search_documents`) and OpenAI chat completion. Pipeline steps are recorded in audit logs.

#### Send message (SSE)

`POST /api/v1/chat/conversations/{session_id}/messages` returns `text/event-stream` with JSON events:

| Event | Payload |
| ----- | ------- |
| `turn_started` | `{ "turn_id": "..." }` |
| `tool_call` | `{ "name": "search_documents" }` |
| `token` | `{ "content": "..." }` |
| `done` | `{ "assistant_message_id": 1, "content": "..." }` |
| `error` | `{ "message": "..." }` |

The client shows the user message optimistically; the server does not echo it in the stream.

See [`docs/chat-sse-streaming.md`](docs/chat-sse-streaming.md) for the full SSE contract, flow, and extension guide.

### Health

| Method | Endpoint               | Description        |
| ------ | ---------------------- | ------------------ |
| `GET`  | `/api/v1/health`       | API liveness       |
| `GET`  | `/api/v1/health/db`    | PostgreSQL check   |
| `GET`  | `/api/v1/health/qdrant`| Qdrant check       |

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## Frontend routes

| Path        | Page           | Access        |
| ----------- | -------------- | ------------- |
| `/`         | redirect       | public        |
| `/login`    | LoginPage      | guest only    |
| `/register` | RegisterPage   | guest only    |
| `/chat`     | ChatPage       | authenticated |
| `/audit`    | AuditLogsPage  | authenticated |

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

## LLM quality benchmark (DeepEval)

Standalone evaluation against the live API (not part of `pytest` or coverage). Pilot covers cases 1 and 10 from [usecases/agent-manual-tests.md](usecases/agent-manual-tests.md).

**Prerequisites:**

```bash
docker compose up --build
docker compose exec backend python -m app.scripts.ingest_documents --force
export OPENAI_API_KEY=sk-...
```

**Install dev deps (once):**

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
```

**Run:**

```bash
python -m app.scripts.run_deepeval --base-url http://localhost:8000
```

Writes `eval_report.json` and prints per-metric scores. Judge model: **gpt-4o**. A case **passes** only when **all** configured metrics pass.

| Case | Answer Relevancy | Faithfulness | Contextual Relevancy / Hallucination | GEval | Pass |
|------|-----------------|--------------|--------------------------------------|-------|------|
| 1 - Laptop safety | 1.00 | 1.00 | Contextual 0.60 | SafetyFacts 1.00 | Yes |
| 10 - No hallucination | 0.75 | 1.00 | Hallucination 0.00 | NoPrinthead 1.00 | Yes |

Last run: **2/2** cases passed (2026-07-04). To extend the suite, add cases to [backend/eval/dataset.py](backend/eval/dataset.py).

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
- LLM quality benchmark (DeepEval): cases 1 and 10 via `python -m app.scripts.run_deepeval`

Not yet implemented:

- Load tests
- Full 10-case DeepEval suite (cases 2–9)

Manual step before RAG answers work: place HP PDFs in `rag-docs/` and run the ingest CLI (see [RAG and document corpus](#rag-and-document-corpus)).
