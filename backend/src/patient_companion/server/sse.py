"""Server-sent events helpers."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi.responses import StreamingResponse

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


def encode_event(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def sse_response(events: Iterator[dict[str, Any]]) -> StreamingResponse:
    return StreamingResponse(
        (encode_event(e) for e in events),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
