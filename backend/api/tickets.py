import time
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db import crud
from backend.models.ticket import InboundTicket
from backend.api.ws import manager
from backend.config import settings

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

# Graph and checkpointer are initialized in main.py and injected here
_graph = None
_checkpointer = None


def set_graph(graph, checkpointer):
    global _graph, _checkpointer
    _graph = graph
    _checkpointer = checkpointer


@router.post("/ingest")
async def ingest_ticket(ticket: InboundTicket, db: Session = Depends(get_db)):
    """
    Entry point for a new customer ticket.

    This kicks off the LangGraph pipeline asynchronously. The pipeline runs
    Nodes 1-3, then pauses at the HITL breakpoint. When it pauses, we:
      1. Update the ticket status in our DB to "awaiting_hitl"
      2. Broadcast a "review_ready" event via WebSocket so the dashboard lights up
    """
    # Persist the inbound ticket
    crud.create_ticket(
        db,
        ticket_id=ticket.ticket_id,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
        order_id=ticket.order_id,
        raw_text=ticket.raw_text,
    )

    # Run the pipeline in the background so the HTTP response returns immediately
    asyncio.create_task(_run_pipeline(ticket, db))

    return {"status": "accepted", "ticket_id": ticket.ticket_id}


def _get_langfuse_callback(ticket_id: str):
    """
    Returns a Langfuse CallbackHandler if credentials are configured, else None.
    Each ticket gets its own handler so traces are grouped by ticket in Langfuse.
    The session_id = ticket_id, so you can filter all node traces for one ticket.
    """
    if not settings.langfuse_enabled:
        return None
    from langfuse.langchain import CallbackHandler
    # Reads LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_HOST from env automatically
    return CallbackHandler()


async def _run_pipeline(ticket: InboundTicket, db: Session):
    from backend.graph.pipeline import get_thread_config

    config = get_thread_config(ticket.ticket_id)

    # Attach Langfuse callback to the graph config — it will trace every
    # LLM call across all three nodes automatically via LangChain's callback system.
    langfuse_cb = _get_langfuse_callback(ticket.ticket_id)
    if langfuse_cb:
        config["callbacks"] = [langfuse_cb]

    initial_state = {
        "ticket": ticket,
        "intent": None,
        "sop_match": None,
        "order_data": None,
        "workspace": None,
        "hitl_decision": None,
        "pipeline_start_ms": int(time.time() * 1000),
        "error": None,
    }

    try:
        # This runs until the interrupt_before=["execute_action"] breakpoint
        await _graph.ainvoke(initial_state, config)

        # At this point the graph is paused. Fetch the checkpointed state.
        state_snapshot = await _graph.aget_state(config)
        workspace = state_snapshot.values.get("workspace")
        error = state_snapshot.values.get("error")

        if error or not workspace:
            crud.update_ticket_status(db, ticket.ticket_id, "error")
            await manager.broadcast({
                "event": "pipeline_error",
                "ticket_id": ticket.ticket_id,
                "error": error or "Pipeline produced no workspace",
            })
            return

        crud.update_ticket_status(db, ticket.ticket_id, "awaiting_hitl")

        # Push the assembled workspace to the human dashboard
        await manager.broadcast({
            "event": "review_ready",
            "ticket_id": ticket.ticket_id,
            "workspace": workspace.model_dump(mode="json"),
        })

    except Exception as e:
        crud.update_ticket_status(db, ticket.ticket_id, "error")
        await manager.broadcast({
            "event": "pipeline_error",
            "ticket_id": ticket.ticket_id,
            "error": str(e),
        })


@router.get("/queue")
def get_queue(db: Session = Depends(get_db)):
    """Return all tickets currently waiting for human review."""
    tickets = crud.get_tickets_by_status(db, "awaiting_hitl")
    return [
        {"ticket_id": t.ticket_id, "customer_name": t.customer_name,
         "order_id": t.order_id, "status": t.status, "created_at": t.created_at}
        for t in tickets
    ]
