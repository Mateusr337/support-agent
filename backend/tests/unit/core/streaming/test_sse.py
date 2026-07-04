from app.core.streaming.sse import SSE_HEADERS, format_sse


def test_format_sse_serializes_event():
    assert format_sse({"type": "token", "content": "Hi"}) == (
        'event: message\ndata: {"type": "token", "content": "Hi"}\n\n'
    )


def test_sse_headers_include_no_cache():
    assert SSE_HEADERS["Cache-Control"] == "no-cache"
    assert SSE_HEADERS["X-Accel-Buffering"] == "no"
