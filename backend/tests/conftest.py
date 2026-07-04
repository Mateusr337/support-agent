import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["QDRANT_URL"] = "http://localhost:6335"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["JWT_SECRET"] = "test-secret-key-for-pytest"
os.environ["JWT_EXPIRE_MINUTES"] = "60"
os.environ["OPENAI_API_KEY"] = ""
os.environ["LLM_PROVIDER"] = "openai"

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.dependencies import get_support_agent
from app.core.database import Base, get_db
from app.main import app
from app.models import ChatMessage, ChatSession, User  # noqa: F401

FAKE_AGENT_REPLY = "Thanks for your message. A support agent will help you shortly."


class FakeSupportAgent:
    async def reply(self, user_message: str, history=None, **kwargs) -> str:
        return FAKE_AGENT_REPLY


@pytest.fixture(autouse=True)
def block_real_openai_api_calls():
    mock_chat_client = MagicMock()
    mock_chat_client.chat.completions.create = AsyncMock(
        side_effect=RuntimeError("OpenAI API must not be called in tests")
    )
    mock_embedding_client = MagicMock()
    mock_embedding_client.embeddings.create = AsyncMock(
        side_effect=RuntimeError("OpenAI API must not be called in tests")
    )
    with (
        patch("app.core.llm.openai.AsyncOpenAI", return_value=mock_chat_client),
        patch(
            "app.rag.embeddings.openai.AsyncOpenAI",
            return_value=mock_embedding_client,
        ),
    ):
        yield


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_support_agent] = lambda: FakeSupportAgent()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    payload = {
        "email": "user@example.com",
        "name": "Test User",
        "password": "password123",
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    return {**payload, **response.json()}


@pytest.fixture()
def auth_headers(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


FULL_COVERAGE_PREFIXES = (
    "app/services/",
    "app/repositories/",
)


def pytest_sessionfinish(session, exitstatus):
    if exitstatus != 0:
        return
    if not session.config.pluginmanager.hasplugin("_cov"):
        return

    from coverage import Coverage

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cov = Coverage()
    cov.load()

    violations: list[str] = []
    for filename in cov.get_data().measured_files():
        rel_path = os.path.relpath(filename, backend_root)
        if not rel_path.startswith("app/"):
            continue
        if not any(rel_path.startswith(prefix) for prefix in FULL_COVERAGE_PREFIXES):
            continue
        analysis = cov.analysis2(filename)
        missing_lines = analysis[3]
        if missing_lines:
            violations.append(f"{rel_path}: missing lines {missing_lines}")

    if violations:
        message = "100% coverage required for services and repositories:\n" + "\n".join(
            violations
        )
        session.config.pluginmanager.getplugin("terminalreporter").write_line(message)
        session.exitstatus = 1
