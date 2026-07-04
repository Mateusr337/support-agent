import json
import time
import uuid
from typing import Any

import httpx
from deepeval.test_case import LLMTestCase

from eval.dataset import EvalCase


class EvalRunnerError(Exception):
    pass


def parse_sse_events(body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in body.strip().split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


def check_health(client: httpx.Client, base_url: str) -> None:
    response = client.get(f"{base_url}/api/v1/health")
    if response.status_code != 200:
        raise EvalRunnerError(
            f"API health check failed ({response.status_code}). "
            f"Is the stack running at {base_url}?"
        )


def register_and_login(client: httpx.Client, base_url: str) -> tuple[str, str]:
    email = f"eval_{uuid.uuid4().hex[:12]}@test.com"
    password = "EvalPass123!"

    register_response = client.post(
        f"{base_url}/api/v1/users",
        json={"email": email, "name": "Eval Bot", "password": password},
    )
    if register_response.status_code not in (201, 409):
        raise EvalRunnerError(
            f"User registration failed ({register_response.status_code}): "
            f"{register_response.text}"
        )

    login_response = client.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if login_response.status_code != 200:
        raise EvalRunnerError(
            f"Login failed ({login_response.status_code}): {login_response.text}"
        )

    return login_response.json()["access_token"], email


def send_message(
    client: httpx.Client,
    base_url: str,
    token: str,
    question: str,
) -> tuple[str, str, str, int]:
    headers = {"Authorization": f"Bearer {token}"}

    session_response = client.post(
        f"{base_url}/api/v1/chat/conversations",
        headers=headers,
    )
    if session_response.status_code != 201:
        raise EvalRunnerError(
            f"Failed to create session ({session_response.status_code}): "
            f"{session_response.text}"
        )
    session_id = session_response.json()["id"]

    start = time.perf_counter()
    message_response = client.post(
        f"{base_url}/api/v1/chat/conversations/{session_id}/messages",
        headers=headers,
        json={"content": question},
        timeout=120.0,
    )
    completion_time_ms = round((time.perf_counter() - start) * 1000)
    if message_response.status_code != 200:
        raise EvalRunnerError(
            f"Failed to send message ({message_response.status_code}): "
            f"{message_response.text}"
        )

    events = parse_sse_events(message_response.text)
    if not events:
        raise EvalRunnerError("No SSE events received from chat endpoint")

    turn_id = next(
        (event["turn_id"] for event in events if event.get("type") == "turn_started"),
        None,
    )
    if turn_id is None:
        raise EvalRunnerError("Missing turn_started event in SSE stream")

    error_event = next(
        (event for event in events if event.get("type") == "error"),
        None,
    )
    if error_event is not None:
        raise EvalRunnerError(f"Chat stream error: {error_event.get('message')}")

    done_event = next(
        (event for event in events if event.get("type") == "done"),
        None,
    )
    if done_event is None:
        raise EvalRunnerError("Missing done event in SSE stream")

    answer = done_event.get("content", "")
    if not answer:
        raise EvalRunnerError("Empty assistant reply in done event")

    return answer, session_id, turn_id, completion_time_ms


def fetch_audit_logs(
    client: httpx.Client,
    base_url: str,
    token: str,
    session_id: str,
    turn_id: str,
) -> list[dict[str, Any]]:
    response = client.get(
        f"{base_url}/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
        params={"session_id": session_id, "turn_id": turn_id, "limit": 50},
    )
    if response.status_code != 200:
        raise EvalRunnerError(
            f"Failed to fetch audit logs ({response.status_code}): {response.text}"
        )
    return response.json()["items"]


def extract_retrieval_context(logs: list[dict[str, Any]]) -> list[str]:
    chunks: list[str] = []
    for log in logs:
        if log.get("type") != "Tool Result":
            continue
        results = log.get("data", {}).get("results") or []
        for result in results:
            text = result.get("text")
            if text:
                chunks.append(text)
    return chunks


def extract_retrieved_sources(logs: list[dict[str, Any]]) -> list[str]:
    sources: set[str] = set()
    for log in logs:
        if log.get("type") != "Tool Result":
            continue
        results = log.get("data", {}).get("results") or []
        for result in results:
            source = result.get("source")
            if source:
                sources.add(source)
    return sorted(sources)


def extract_latency_from_logs(logs: list[dict[str, Any]]) -> dict[str, list[int]]:
    llm_latency_ms: list[int] = []
    tool_latency_ms: list[int] = []

    for log in logs:
        data = log.get("data") or {}
        latency_ms = data.get("latency_ms")
        if latency_ms is None:
            continue

        if log.get("type") == "Tool Result":
            tool_latency_ms.append(int(latency_ms))
            continue

        if log.get("message") in ("LLM response", "LLM stream response"):
            llm_latency_ms.append(int(latency_ms))

    return {
        "llm_latency_ms": llm_latency_ms,
        "tool_latency_ms": tool_latency_ms,
    }


def build_test_case(
    case: EvalCase,
    answer: str,
    retrieval_context: list[str],
    *,
    completion_time_ms: int,
) -> LLMTestCase:
    return LLMTestCase(
        input=case.input,
        actual_output=answer,
        expected_output=case.expected_output,
        retrieval_context=retrieval_context,
        context=retrieval_context,
        completion_time=completion_time_ms / 1000,
    )


def collect_case_data(
    client: httpx.Client,
    base_url: str,
    token: str,
    case: EvalCase,
) -> tuple[LLMTestCase, list[str], dict[str, Any]]:
    answer, session_id, turn_id, completion_time_ms = send_message(
        client, base_url, token, case.input
    )
    logs = fetch_audit_logs(client, base_url, token, session_id, turn_id)
    retrieval_context = extract_retrieval_context(logs)
    sources = extract_retrieved_sources(logs)
    test_case = build_test_case(
        case,
        answer,
        retrieval_context,
        completion_time_ms=completion_time_ms,
    )
    latency = extract_latency_from_logs(logs)
    return test_case, sources, {
        "completion_time_ms": completion_time_ms,
        "latency": latency,
    }
