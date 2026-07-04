import json

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def format_sse(event: dict) -> str:
    return f"event: message\ndata: {json.dumps(event)}\n\n"
