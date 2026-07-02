from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.qdrant import get_qdrant_client

app = FastAPI(title="Support Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/health/qdrant")
def health_qdrant():
    get_qdrant_client().get_collections()
    return {"status": "ok", "qdrant": "connected"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from Support Agent API"}
