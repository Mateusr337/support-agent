# support-agent

## Problem

You have to develop a ChatBot that answers questions about HP documents using Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG).

You have to develop this application end-to-end, and make it available in GitHub repository.

The application has the following requirements:

- [x] Frontend with Graphical Interface, of your own choosing, to provide user interaction.
- [x] Backend must run with Python code using FastAPI.
- [x] Backend must have unit tests with at least 90% of coverage.
- [ ] You can use either cloud or local (open source) models, of your own choosing. *(OpenAI wired to chat; local models not yet supported)*
- [x] Must use an open-source Vector Database for performing RAG. *(Qdrant connected; ingestion pending)*
- [ ] Must use only the attached documents for building the Vector Database.
- [ ] Must use a Chunking Strategy to index the document on the Vector Database.
- [ ] Must select a Search Strategy for retrieval.
- [x] Must have support for conversation with chat history.
- [x] Must store the user chats and history in the backend.
- [x] Must run through Docker Compose, where all the application and necessary dependencies are containerized.
- [ ] Scalability must be ensured with load tests (how many requests per minute the solution supports)
- [ ] Must benchmark the quality of the LLM responses to the user.

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
├── documents/          # HP PDF corpus (indexed manually via ingest CLI)
├── backend/              # FastAPI API
├── frontend/             # React SPA (TypeScript)
├── docker-compose.yml
├── .env.example          # Docker Compose env (copy to .env)
└── .cursor/rules/        # Architecture conventions
```

Architecture details: `.cursor/rules/backend-architecture.mdc` and `.cursor/rules/frontend-architecture.mdc`.

## RAG and document corpus

HP PDFs live in **`documents/`** at the repo root. They are **not** baked into the Docker image and are **not** indexed on container startup.

| Concern | Location / mechanism |
| ------- | -------------------- |
| PDF files | `documents/*.pdf` |
| Ingest CLI (planned) | `backend/app/scripts/ingest_documents.py` |
| Ingest + search logic (planned) | `backend/app/rag/service.py` |
| Vector storage | Qdrant collection (`QDRANT_COLLECTION`) |
| Chat retrieval | `tools/search_documents` → `RagService.search()` (agent never reads `documents/`) |

After adding PDFs, index manually:

```bash
# Local backend
cd backend
source .venv/bin/activate
python -m app.scripts.ingest_documents

# Or with the backend container running
docker compose exec backend python -m app.scripts.ingest_documents
```

Docker mounts `./documents` read-only at `/app/documents` inside the backend container (`DOCUMENTS_DIR`).

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
| `DOCUMENTS_DIR`      | Folder with HP PDFs (Compose default: `/app/documents`) |
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
| `GET`  | `/api/v1/chat/conversations/{session_id}/messages` | List messages, paginated (`limit`, `offset`; default `10`) |
| `POST` | `/api/v1/chat/conversations/{session_id}/messages` | Send a message (`201`; returns user + assistant messages) |

Assistant replies are currently a stub until RAG and LLM are wired into `ChatService`.

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

## Backend tests

Tests use **pytest**, **pytest-cov**, and **httpx** (`backend/requirements-dev.txt`). They run on the host, not inside the backend container (the Docker image installs only `requirements.txt`).

Tests use an in-memory SQLite database (no Postgres required). Override `get_db` via `app.dependency_overrides` in `conftest.py`.

Current coverage: **~95%** on `app/` (71 tests).

```bash
cd backend
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest                              # run all tests
pytest --cov=app --cov-report=term-missing   # with coverage %
pytest --cov=app --cov-report=html           # HTML report → htmlcov/index.html
```

Layout mirrors the backend layers — see `.cursor/rules/backend-architecture.mdc` (Testing section).

## Current status

Implemented:

- Docker Compose with PostgreSQL, Qdrant, backend, and frontend
- Alembic migrations (users, chat sessions, chat messages)
- Health endpoints: `/api/v1/health`, `/api/v1/health/db`, `/api/v1/health/qdrant`
- Auth: register, login, JWT, `/api/v1/auth/me`
- Chat API: sessions, message storage, pagination, LLM assistant replies with chat history
- Frontend: auth (login / register), protected chat UI wired to the chat API
- LLM integration: `core/llm/` adapters and `SupportAgent` wired into `ChatService`
- Backend test suite with ~95% coverage

Not yet implemented:

- RAG pipeline (`rag/service.py`, `vector_repository.py`, ingest CLI implementation)
- HP document indexing into Qdrant
- Load tests and quality benchmarks

Architecture declared: `documents/` folder, `DOCUMENTS_DIR`, Docker volume mount, manual ingest workflow (see `.cursor/rules/backend-architecture.mdc`).
