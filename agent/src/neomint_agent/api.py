"""FastAPI server for the NeoMint agent.

Exposes the agent loop to the overlay UI via REST and WebSocket endpoints.
WebSocket provides streaming updates for plan generation and execution.

Endpoints:
    POST /api/request       — submit a natural language request
    POST /api/approve/{hash} — approve a pending plan
    POST /api/cancel/{hash}  — cancel a pending plan
    GET  /api/status        — agent health, model status, pending plans
    GET  /api/history       — recent audit events
    WS   /ws                — streaming updates
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from neomint_agent import __version__
from neomint_agent.audit import AuditLogger
from neomint_agent.config import AGENT_HOST, AGENT_PORT, LOG_LEVEL, OLLAMA_MODEL
from neomint_agent.loop import AgentLoop
from neomint_agent.model_adapter import OllamaAdapter
from neomint_agent.schemas import AgentResponse
from neomint_agent.tool_executor import ToolExecutor

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("neomint-agent.api")

# ── Global state ─────────────────────────────────────────────

agent_loop: AgentLoop | None = None
ws_clients: set[WebSocket] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global agent_loop
    agent_loop = AgentLoop()
    logger.info("NeoMint Agent v%s started on %s:%d", __version__, AGENT_HOST, AGENT_PORT)
    yield
    if agent_loop:
        await agent_loop.close()
    logger.info("NeoMint Agent shut down")


app = FastAPI(
    title="NeoMint Agent",
    version=__version__,
    description="Local LLM-powered desktop action planner",
    lifespan=lifespan,
)

# CORS for localhost overlay UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:1420",   # Tauri dev server
        "http://localhost:5173",   # Vite dev server
        "http://127.0.0.1:1420",
        "http://127.0.0.1:5173",
        "tauri://localhost",       # Tauri production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request models ───────────────────────────────────────────


class RequestBody(BaseModel):
    text: str


# ── WebSocket broadcast ──────────────────────────────────────


async def broadcast(event: dict[str, Any]) -> None:
    """Send an event to all connected WebSocket clients."""
    message = json.dumps(event, default=str)
    disconnected: set[WebSocket] = set()

    for ws in ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)

    ws_clients -= disconnected


# ── REST endpoints ───────────────────────────────────────────


@app.post("/api/request", response_model=AgentResponse)
async def submit_request(body: RequestBody) -> AgentResponse:
    """Submit a natural language request to the agent."""
    assert agent_loop is not None

    # Broadcast planning state
    await broadcast({"type": "state", "state": "planning", "request": body.text})

    response = await agent_loop.process_request(body.text)

    # Broadcast result
    await broadcast({
        "type": "response",
        "status": response.status,
        "message": response.message,
        "plan": response.plan.model_dump() if response.plan else None,
        "results": [r.model_dump() for r in response.results] if response.results else None,
    })

    return response


@app.post("/api/approve/{plan_hash}", response_model=AgentResponse)
async def approve_plan(plan_hash: str) -> AgentResponse:
    """Approve a pending plan for execution."""
    assert agent_loop is not None

    await broadcast({"type": "state", "state": "executing", "plan_hash": plan_hash})

    response = await agent_loop.approve_plan(plan_hash)

    await broadcast({
        "type": "response",
        "status": response.status,
        "message": response.message,
        "results": [r.model_dump() for r in response.results] if response.results else None,
    })

    return response


@app.post("/api/cancel/{plan_hash}", response_model=AgentResponse)
async def cancel_plan(plan_hash: str) -> AgentResponse:
    """Cancel a pending plan."""
    assert agent_loop is not None

    response = await agent_loop.cancel_plan(plan_hash)

    await broadcast({
        "type": "response",
        "status": response.status,
        "message": response.message,
    })

    return response


@app.get("/api/status")
async def get_status() -> dict[str, Any]:
    """Get agent health status."""
    assert agent_loop is not None

    model_available = await agent_loop.model.is_available()

    return {
        "version": __version__,
        "model": OLLAMA_MODEL,
        "model_available": model_available,
        "pending_plans": agent_loop.pending_plan_count,
        "tools_available": agent_loop.executor.is_available,
        "ws_clients": len(ws_clients),
    }


@app.get("/api/history")
async def get_history(count: int = 20) -> dict[str, Any]:
    """Get recent audit events."""
    assert agent_loop is not None

    events = agent_loop.audit.read_recent(count)
    return {"events": events, "count": len(events)}


# ── WebSocket endpoint ───────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket for streaming agent updates to the UI."""
    await websocket.accept()
    ws_clients.add(websocket)
    logger.info("WebSocket client connected (%d total)", len(ws_clients))

    try:
        while True:
            # Keep connection alive, process incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "request":
                    text = message.get("text", "")
                    if text and agent_loop:
                        response = await agent_loop.process_request(text)
                        await websocket.send_text(
                            json.dumps({
                                "type": "response",
                                "status": response.status,
                                "message": response.message,
                                "plan": response.plan.model_dump() if response.plan else None,
                                "results": [r.model_dump() for r in response.results] if response.results else None,
                            }, default=str)
                        )

                elif msg_type == "approve":
                    plan_hash = message.get("plan_hash", "")
                    if plan_hash and agent_loop:
                        response = await agent_loop.approve_plan(plan_hash)
                        await websocket.send_text(
                            json.dumps({
                                "type": "response",
                                "status": response.status,
                                "message": response.message,
                                "results": [r.model_dump() for r in response.results] if response.results else None,
                            }, default=str)
                        )

                elif msg_type == "cancel":
                    plan_hash = message.get("plan_hash", "")
                    if plan_hash and agent_loop:
                        response = await agent_loop.cancel_plan(plan_hash)
                        await websocket.send_text(
                            json.dumps({
                                "type": "response",
                                "status": response.status,
                                "message": response.message,
                            }, default=str)
                        )

                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid JSON"})
                )

    except WebSocketDisconnect:
        pass
    finally:
        ws_clients.discard(websocket)
        logger.info("WebSocket client disconnected (%d remaining)", len(ws_clients))


# ── Entry point ──────────────────────────────────────────────


def main() -> None:
    """Run the agent API server."""
    uvicorn.run(
        "neomint_agent.api:app",
        host=AGENT_HOST,
        port=AGENT_PORT,
        reload=False,
        log_level=LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
