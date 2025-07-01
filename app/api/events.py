from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.responses import JSONResponse
from typing import Dict
import time
import asyncio
import logging

router = APIRouter(prefix="/ws", tags=["events"])

# Simple in-memory rate limiter (token -> [timestamps])
# For production, replace with Redis or database-backed limiter.
_RATE_LIMIT_WINDOW = 60  # seconds
_RATE_LIMIT_MAX = 120  # max messages per window (approx 2 msg/s)
_token_usage: Dict[str, list[float]] = {}
_logger = logging.getLogger("agent_ws")


async def _check_rate_limit(token: str) -> bool:
    """Return True if allowed, False if rate-limit exceeded."""
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW
    timestamps = _token_usage.setdefault(token, [])
    # Drop timestamps outside window
    _token_usage[token] = [ts for ts in timestamps if ts >= window_start]
    if len(_token_usage[token]) >= _RATE_LIMIT_MAX:
        return False
    _token_usage[token].append(now)
    return True


@router.websocket("/agent-events")
async def agent_events_socket(ws: WebSocket):
    """WebSocket endpoint that streams agent plan events to the client.

    The client must supply a `token` query parameter for authentication. A very
    lightweight in-memory rate limiter is applied per token.
    """
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Accept the WebSocket connection
    await ws.accept()
    _logger.info("Agent WS connected token=%s ip=%s", token, ws.client.host)

    try:
        while True:
            # FastAPI requires reading from the socket to detect disconnects.
            try:
                msg = await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send ping every 30s to keep connection alive
                await ws.send_json({"type": "ping", "ts": time.time()})
                continue

            if msg == "ping":
                await ws.send_text("pong")
                continue

            # Enforce rate limit on incoming messages (rare; usually server push)
            allowed = await _check_rate_limit(token)
            if not allowed:
                _logger.warning("Rate limit exceeded token=%s", token)
                await ws.send_json({"type": "error", "detail": "rate_limit"})
                continue

            # Currently, this WS is server-push only, so ignore incoming.
            _logger.debug("Received client message token=%s: %s", token, msg)
    except WebSocketDisconnect:
        _logger.info("Agent WS disconnected token=%s", token)
    finally:
        # Clean up usage to avoid mem-leak
        _token_usage.pop(token, None)
