"""
HITL Decision Endpoints

These are the routes the human agent dashboard calls when they click
Approve / Edit+Approve / Reject.

FLOW:
    1. Human clicks a button on the dashboard.
    2. Frontend POSTs to /api/hitl/{ticket_id}/decide with a HITLDecision payload.
    3. We inject the decision into the checkpointed graph state.
    4. We call graph.invoke(None, config) to RESUME the graph.
    5. execute_action node runs with the human's decision baked in.
    6. We save the audit log and push a "completed" WebSocket event.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.db import crud
from backend.models.ticket import HITLDecision
from backend.api.ws import manager

router = APIRouter(prefix="/api/hitl", tags=["hitl"])

_graph = None


def set_graph(graph):
    global _graph
    _graph = graph


@router.post("/{ticket_id}/decide")
async def submit_hitl_decision(
    ticket_id: str,
    decision: HITLDecision,
    db: Session = Depends(get_db),
):
    from backend.graph.pipeline import get_thread_config

    config = get_thread_config(ticket_id)

    # Verify the thread exists and is paused at the HITL breakpoint
    state_snapshot = await _graph.aget_state(config)
    if not state_snapshot or not state_snapshot.values.get("workspace"):
        raise HTTPException(status_code=404, detail=f"No pending HITL state for ticket {ticket_id}")

    # Inject the human's decision into the graph state
    await _graph.aupdate_state(config, {"hitl_decision": decision})

    # Resume the graph — execute_action node will now run
    await _graph.ainvoke(None, config)

    # Fetch final state from checkpointer to get the audit entry
    final_snapshot = await _graph.aget_state(config)
    audit_entry = final_snapshot.values.get("audit_entry")
    if audit_entry:
        crud.save_audit_log(db, audit_entry)

    crud.update_ticket_status(
        db, ticket_id,
        "completed" if decision.action.value != "reject" else "rejected"
    )

    # Notify all connected dashboard clients
    await manager.broadcast({
        "event": "ticket_resolved",
        "ticket_id": ticket_id,
        "action": decision.action.value,
        "human_agent_id": decision.human_agent_id,
    })

    return {
        "status": "resolved",
        "ticket_id": ticket_id,
        "action": decision.action.value,
    }


@router.get("/{ticket_id}/state")
async def get_ticket_state(ticket_id: str):
    """Return the current checkpointed state for a ticket (for dashboard load on page refresh)."""
    from backend.graph.pipeline import get_thread_config
    config = get_thread_config(ticket_id)
    state_snapshot = await _graph.aget_state(config)
    if not state_snapshot:
        raise HTTPException(status_code=404, detail="Ticket state not found")
    workspace = state_snapshot.values.get("workspace")
    if not workspace:
        raise HTTPException(status_code=404, detail="Pipeline not yet complete for this ticket")
    return {"workspace": workspace.model_dump(mode="json")}
