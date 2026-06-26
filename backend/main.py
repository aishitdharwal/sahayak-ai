"""
Sahayak AI — FastAPI Application Entry Point

Startup sequence:
    1. Initialize SQLite databases (app DB + LangGraph checkpoint DB)
    2. Build the LangGraph pipeline with the checkpointer
    3. Inject graph + checkpointer into the API routers
    4. Mount CORS and WebSocket routes
"""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv(override=True)  # override=True ensures .env values win over any stale shell exports
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from backend.config import settings
from backend.db.session import init_db
from backend.graph.pipeline import build_graph
from backend.api import tickets as tickets_router
from backend.api import hitl as hitl_router
from backend.api.ws import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize application database tables
    init_db()

    # AsyncSqliteSaver uses aiosqlite — required for ainvoke/aget_state in async FastAPI handlers.
    # EC2 teaching note: this is still single-file SQLite, just async-safe.
    # ECS upgrade path: swap for AsyncPostgresSaver — same interface, different backend.
    async with AsyncSqliteSaver.from_conn_string(settings.graph_checkpoint_db) as checkpointer:
        graph = build_graph(checkpointer)

        # Inject into API routers (avoids circular imports)
        tickets_router.set_graph(graph, checkpointer)
        hitl_router.set_graph(graph)

        print("Sahayak AI backend ready.")
        yield


app = FastAPI(
    title="Sahayak AI",
    description="Flipkart-inspired HITL Agent Assist Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router.router)
app.include_router(hitl_router.router)


@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    """
    Single WebSocket endpoint for the human agent dashboard.

    DESIGN DECISION: One shared channel vs. per-ticket channels.

    One shared channel (this implementation):
        PRO: Simple. Dashboard always connected regardless of which ticket comes in.
        CON: Every agent sees events for all tickets. For a demo with 1-2 agents, ideal.

    Per-ticket channels (/ws/agent/{ticket_id}):
        PRO: Scoped notifications. Agent only sees their assigned tickets.
        CON: Agent must reconnect when they navigate to a different ticket.

    For the workshop demo, one shared channel is correct.
    """
    await manager.connect("broadcast", websocket)
    try:
        while True:
            # Keep connection alive — client sends pings, we just wait
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("broadcast")


@app.get("/health")
def health():
    return {"status": "ok", "service": "sahayak-ai"}
