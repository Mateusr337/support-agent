# support-agent

## Problem

You have to develop a ChatBot that answers questions about HP documents using Large Language Models (LLMs) with Retrieval-Augmented Generation (RAG).

You have to develop this application end-to-end, and make it available in GitHub repository.

The application has the following requirements:

- [ ] Frontend with Graphical Interface, of your own choosing, to provide user interaction.
- [ ] Backend must run with Python code using FastAPI. 
- [ ] Backend must have unit tests with at least 90% of coverage.
- [ ] You can use either cloud or local (open source) models, of your own choosing.
- [ ] Must use an open-source Vector Database for performing RAG.
- [ ] Must use only the attached documents for building the Vector Database.
- [ ] Must use a Chunking Strategy to index the document on the Vector Database.
- [ ] Must select a Search Strategy for retrieval. 
- [ ] Must have support for conversation with chat history.
- [ ] Must store the user chats and history in the backend.
- [ ] Must run through Docker Compose, where all the application and necessary dependencies are containerized.
- [ ] Scalability must be ensured with load tests (how many requests per minute the solution supports)
- [ ] Must benchmark the quality of the LLM responses to the user.

## Overview

Monorepo with a React frontend and a FastAPI backend, orchestrated via Docker Compose. PostgreSQL stores relational data; Qdrant serves as the vector database for RAG.

| Layer | Stack |
|-------|-------|
| Frontend | React 19, Vite |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 16 |
| Vector DB | Qdrant 1.12 |

## Project structure

```
support-agent/
├── backend/          # FastAPI API
├── frontend/         # React SPA
├── docker-compose.yml
├── .env.example      # Docker Compose env (copy to .env)
└── .cursor/rules/    # Architecture conventions
```

Architecture details: `.cursor/rules/backend-architecture.mdc` and `.cursor/rules/frontend-architecture.mdc`.

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

3. Open:

   | Service | URL |
   |---------|-----|
   | Frontend | http://localhost:5173 |
   | Backend API | http://localhost:8000 |
   | API docs | http://localhost:8000/docs |
   | Qdrant dashboard | http://localhost:6335/dashboard |

## Local development (without Docker)

Run infrastructure only with Compose, then start backend and frontend on the host:

```bash
docker compose up db qdrant
```

**Backend**

```bash
cd backend
cp .env.example .env
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend**

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## Environment variables

Three env files, each for a different context:

| File | Used when |
|------|-----------|
| `.env` (from `.env.example`) | `docker compose up` — all services |
| `backend/.env` (from `backend/.env.example`) | Local FastAPI dev |
| `frontend/.env` (from `frontend/.env.example`) | Local Vite dev (`npm run dev`) |

Root `.env` variables (required for Compose):

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | PostgreSQL database name |
| `QDRANT_URL` | Qdrant URL inside Docker network |
| `QDRANT_HTTP_PORT` | Qdrant HTTP port on host |
| `QDRANT_GRPC_PORT` | Qdrant gRPC port on host |
| `CORS_ORIGINS` | Allowed frontend origins (backend) |
| `JWT_SECRET` | Secret key for signing JWT access tokens |
| `JWT_EXPIRE_MINUTES` | Access token lifetime in minutes (default: `60`) |
| `VITE_API_URL` | Backend URL exposed to the browser |

`backend/.env` also requires `JWT_SECRET` and `JWT_EXPIRE_MINUTES` for local FastAPI dev.

## API (auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/users` | Register a new user (`201`, `409` if email exists) |
| `POST` | `/api/v1/auth/login` | Login (`200` + JWT, `401` on invalid credentials) |
| `GET` | `/api/v1/auth/me` | Current user from JWT (`401` if token invalid) |

Interactive docs: http://localhost:8000/docs

## Current status

Implemented:

- Docker Compose with PostgreSQL, Qdrant, backend, and frontend
- Health endpoints: `/api/v1/health`, `/api/v1/health/db`, `/api/v1/health/qdrant`
- User model, Alembic migrations, register (`POST /api/v1/users`) and login (`POST /api/v1/auth/login`) with JWT
- Frontend status dashboard wired to the API

Not yet implemented:

- Frontend auth (login / register UI)
- Chat UI and conversation history
- RAG pipeline (document ingestion, chunking, retrieval)
- LLM integration
- Unit tests and load/quality benchmarks
