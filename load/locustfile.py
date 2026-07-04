"""
Locust load tests for the Support Agent API.

Mode A (infra, no OpenAI): LOAD_MODE=A (default), LOAD_TEST=true on backend.
Mode B (real agent):        LOAD_MODE=B, LOAD_TEST=false, PDFs ingested, OPENAI_API_KEY set.

Examples:
  # Mode A — headless
  locust -f load/locustfile.py --host http://localhost:8000 \\
    --headless -u 50 -r 5 -t 5m

  # Mode B — headless (start small; each turn calls OpenAI)
  LOAD_MODE=B locust -f load/locustfile.py --host http://localhost:8000 \\
    --headless -u 5 -r 1 -t 5m

  # Interactive UI
  locust -f load/locustfile.py --host http://localhost:8000
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections.abc import Iterator

import requests
from locust import HttpUser, between, events, task
from locust.exception import StopUser

LOAD_MODE = os.getenv("LOAD_MODE", "A").upper()
API_PREFIX = "/api/v1"
DEFAULT_PASSWORD = "password123"
MODE_A_CHAT_MESSAGE = "Load test seed message for audit logs."
MODE_B_CHAT_MESSAGE = (
    "What are the safety tips for using the OMEN 17 inch gaming laptop on my lap?"
)
SSE_TIMEOUT_SECONDS = int(os.getenv("SSE_TIMEOUT_SECONDS", "120"))


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _parse_sse_block(block: str) -> dict | None:
    for line in block.split("\n"):
        if line.startswith("data: "):
            return json.loads(line[6:])
    return None


def _iter_sse_events(response) -> Iterator[dict]:
    buffer = ""
    for chunk in response.iter_content(chunk_size=1024):
        if not chunk:
            continue
        buffer += chunk.decode("utf-8", errors="ignore")
        while "\n\n" in buffer:
            block, buffer = buffer.split("\n\n", 1)
            event = _parse_sse_block(block)
            if event is not None:
                yield event

    if buffer.strip():
        event = _parse_sse_block(buffer)
        if event is not None:
            yield event


def _consume_sse_stream(response) -> tuple[bool, str | None, float | None]:
    start = time.perf_counter()
    first_token_at: float | None = None
    got_done = False

    for event in _iter_sse_events(response):
        event_type = event.get("type")
        if event_type == "token" and first_token_at is None:
            first_token_at = time.perf_counter() - start
        if event_type == "done":
            got_done = True
            break
        if event_type == "error":
            return False, str(event.get("message", "SSE error")), first_token_at

    if got_done:
        return True, None, first_token_at

    return False, "Stream ended without done event", first_token_at


def _register_and_login(client, email: str, password: str) -> str | None:
    with client.post(
        f"{API_PREFIX}/users",
        json={"email": email, "name": "Load Test User", "password": password},
        name=f"{API_PREFIX}/users [register]",
        catch_response=True,
    ) as register_response:
        if register_response.status_code not in (201, 409):
            register_response.failure(
                f"Register failed: HTTP {register_response.status_code} "
                f"{register_response.text[:200]}"
            )
            return None

    with client.post(
        f"{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
        name=f"{API_PREFIX}/auth/login",
        catch_response=True,
    ) as login_response:
        if login_response.status_code != 200:
            login_response.failure(
                f"Login failed: HTTP {login_response.status_code} "
                f"{login_response.text[:200]}"
            )
            return None
        return login_response.json()["access_token"]


def _ensure_session(client, token: str) -> str | None:
    with client.get(
        f"{API_PREFIX}/chat/conversations/active",
        headers=_auth_headers(token),
        name=f"{API_PREFIX}/chat/conversations/active",
        catch_response=True,
    ) as response:
        if response.status_code != 200:
            response.failure(f"Active session failed: HTTP {response.status_code}")
            return None
        return response.json()["id"]


if LOAD_MODE == "B":

    class LoadTestUser(HttpUser):
        """Real agent chat over SSE (OpenAI + RAG). Requires ingested PDFs."""

        wait_time = between(3, 8)

        def on_start(self) -> None:
            self.email = f"load-b-{uuid.uuid4().hex[:12]}@example.com"
            self.password = DEFAULT_PASSWORD
            token = _register_and_login(self.client, self.email, self.password)
            if token is None:
                raise StopUser()
            self.token = token
            session_id = _ensure_session(self.client, self.token)
            if session_id is None:
                raise StopUser()
            self.session_id = session_id

        @task
        def chat_turn(self) -> None:
            turn_start = time.perf_counter()

            with self.client.post(
                f"{API_PREFIX}/chat/conversations/{self.session_id}/messages",
                headers={
                    **_auth_headers(self.token),
                    "Accept": "text/event-stream",
                },
                json={"content": MODE_B_CHAT_MESSAGE},
                stream=True,
                timeout=SSE_TIMEOUT_SECONDS,
                name=f"{API_PREFIX}/chat/messages [SSE turn]",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")
                    return

                success, error, ttft = _consume_sse_stream(response)
                turn_duration = time.perf_counter() - turn_start

                if ttft is not None:
                    events.request.fire(
                        request_type="SSE",
                        name="time_to_first_token",
                        response_time=ttft * 1000,
                        response_length=0,
                        exception=None,
                        context={},
                    )

                if success:
                    response.success()
                    events.request.fire(
                        request_type="SSE",
                        name="turn_complete",
                        response_time=turn_duration * 1000,
                        response_length=0,
                        exception=None,
                        context={},
                    )
                else:
                    response.failure(error or "Chat SSE failed")

else:

    class LoadTestUser(HttpUser):
        """Login, seed one fake chat turn, then browse audit logs."""

        wait_time = between(1, 3)

        def on_start(self) -> None:
            self.email = f"load-a-{uuid.uuid4().hex[:12]}@example.com"
            self.password = DEFAULT_PASSWORD
            token = _register_and_login(self.client, self.email, self.password)
            if token is None:
                raise StopUser()
            self.token = token
            session_id = _ensure_session(self.client, self.token)
            if session_id is None:
                raise StopUser()
            self.session_id = session_id
            self._seed_audit_logs()

        def _seed_audit_logs(self) -> None:
            with self.client.post(
                f"{API_PREFIX}/chat/conversations/{self.session_id}/messages",
                headers={
                    **_auth_headers(self.token),
                    "Accept": "text/event-stream",
                },
                json={"content": MODE_A_CHAT_MESSAGE},
                stream=True,
                timeout=SSE_TIMEOUT_SECONDS,
                name=f"{API_PREFIX}/chat/messages [seed SSE]",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Seed chat failed: HTTP {response.status_code}")
                    return

                success, error, _ = _consume_sse_stream(response)
                if success:
                    response.success()
                else:
                    response.failure(error or "Seed chat SSE failed")

        @task(3)
        def list_audit_logs(self) -> None:
            with self.client.get(
                f"{API_PREFIX}/audit/logs",
                headers=_auth_headers(self.token),
                params={"limit": 25},
                name=f"{API_PREFIX}/audit/logs",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")

        @task(2)
        def list_audit_logs_paginated(self) -> None:
            with self.client.get(
                f"{API_PREFIX}/audit/logs",
                headers=_auth_headers(self.token),
                params={"limit": 25},
                name=f"{API_PREFIX}/audit/logs [page 1]",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")
                    return
                payload = response.json()

            if not payload.get("has_more") or not payload.get("items"):
                return

            last_id = payload["items"][-1]["id"]
            with self.client.get(
                f"{API_PREFIX}/audit/logs",
                headers=_auth_headers(self.token),
                params={"limit": 25, "offset": last_id},
                name=f"{API_PREFIX}/audit/logs [page 2]",
                catch_response=True,
            ) as page_response:
                if page_response.status_code != 200:
                    page_response.failure(f"HTTP {page_response.status_code}")

        @task(1)
        def login_again(self) -> None:
            with self.client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": self.email, "password": self.password},
                name=f"{API_PREFIX}/auth/login [repeat]",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")
                    return
                self.token = response.json()["access_token"]


@events.init.add_listener
def on_locust_init(environment, **_kwargs) -> None:
    print(f"\n[load] Running Locust in Mode {LOAD_MODE}\n")


@events.test_start.add_listener
def on_test_start(environment, **_kwargs) -> None:
    host = (environment.host or "").rstrip("/")
    if not host:
        print("\n[load] ERROR: pass --host http://localhost:8000\n")
        environment.runner.quit()
        return

    try:
        response = requests.get(f"{host}{API_PREFIX}/health", timeout=5)
        if response.status_code != 200:
            print(
                f"\n[load] ERROR: API not healthy at {host} "
                f"(HTTP {response.status_code}). Run: docker compose up -d\n"
            )
            environment.runner.quit()
    except requests.RequestException as exc:
        print(
            f"\n[load] ERROR: cannot reach API at {host} ({exc}). "
            "Run: docker compose up -d\n"
        )
        environment.runner.quit()
