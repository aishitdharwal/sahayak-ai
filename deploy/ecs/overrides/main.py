"""
ECS main.py

Diff from EC2 main.py:
  1. SqliteSaver → AsyncPostgresSaver (RDS Postgres)
  2. lifespan starts the Redis subscriber background task
  3. CORS origin is CloudFront URL instead of localhost

Everything else is identical.
"""

from contextlib import asynccontextmanager
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ECS: AsyncPostgresSaver instead of SqliteSaver
# Package: pip install langgraph-checkpoint-postgres
# TRADEOFF: AsyncPostgresSaver requires a running Postgres instance (RDS).
# SqliteSaver needs zero infrastructure — just a file path.
# In return you get: concurrent access, no file locking, no EFS dependency for checkpoints.
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from backend.config import settings
from backend.db.session import init_db
from backend.graph.pipeline import build_graph
from backend.api import tickets as tickets_router
from backend.api import hitl as hitl_router

# ECS: Redis-backed manager instead of in-memory
from deploy.ecs.overrides.api.ws import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # ECS: AsyncPostgresSaver — one line change from SqliteSaver.
    # Uses the same postgres_url for both the app DB and LangGraph checkpoints.
    async with AsyncPostgresSaver.from_conn_string(settings.postgres_url) as checkpointer:
        await checkpointer.setup()  # Creates checkpoint tables if they don't exist

        graph = build_graph(checkpointer)
        tickets_router.set_graph(graph, checkpointer)
        hitl_router.set_graph(graph)

        # ECS: Start the Redis subscriber background task.
        # This task runs for the lifetime of this Fargate task and forwards
        # Redis pub/sub messages to local WebSocket connections.
        subscriber_task = asyncio.create_task(manager.run_subscriber())

        print("Sahayak AI ECS backend ready.")
        yield

        subscriber_task.cancel()


app = FastAPI(
    title="Sahayak AI",
    description="Flipkart-inspired HITL Agent Assist Platform — ECS",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # ECS: CloudFront URL replaces localhost
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router.router)
app.include_router(hitl_router.router)


@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect("broadcast", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect("broadcast")


@app.get("/health")
def health():
    return {"status": "ok", "service": "sahayak-ai-ecs"}
