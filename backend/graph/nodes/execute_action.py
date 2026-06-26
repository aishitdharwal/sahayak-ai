"""
Node 4: Execute Action (runs AFTER human approval)

This node only runs after the HITL breakpoint is cleared.
By the time execution reaches here, state["hitl_decision"] has been
injected by the API and the human has made their choice.

DESIGN DECISION: Why have an execute_action node at all, rather than
calling the OMS directly from the API?

Keeping execution inside the graph means:
1. The audit trail is automatic — LangSmith traces the full run including this node.
2. The checkpointer captures the final state including execution results.
3. It's easy to add retry logic, compensating transactions, or notification steps
   as additional nodes AFTER this one without touching the API layer.

In production this node would call real OMS mutation APIs with the parameters
pre-validated by the HITL stage.
"""

import uuid
from datetime import datetime
from backend.graph.state import AgentState
from backend.models.ticket import HITLAction
from backend.models.audit import AuditLogEntry


async def execute_action_node(state: AgentState) -> dict:
    decision = state["hitl_decision"]
    workspace = state["workspace"]

    if decision.action == HITLAction.REJECT:
        # Human rejected — log and route to manual queue, no OMS mutation
        return {
            "audit_entry": _build_audit(state, executed=False),
        }

    # Approve or Edit+Approve — execute the staged action
    # In production: call OMS mutation API here with workspace.order_data.order_id
    # e.g. await oms_client.initiate_refund(order_id=..., amount=..., reason=...)
    print(f"[EXECUTOR] Sending response to {workspace.ticket.customer_email}")
    print(f"[EXECUTOR] Response: {decision.final_response}")
    print(f"[EXECUTOR] Would call OMS for order {workspace.order_data.order_id}")

    return {
        "audit_entry": _build_audit(state, executed=True),
    }


def _build_audit(state: AgentState, executed: bool) -> AuditLogEntry:
    decision = state["hitl_decision"]
    workspace = state["workspace"]
    start_ms = state.get("pipeline_start_ms", 0)
    elapsed = int(datetime.utcnow().timestamp() * 1000) - (start_ms or 0)

    ai_draft = workspace.draft_response
    human_final = decision.final_response
    edit_dist = sum(1 for a, b in zip(ai_draft, human_final) if a != b) + abs(len(ai_draft) - len(human_final))

    return AuditLogEntry(
        log_id=str(uuid.uuid4()),
        ticket_id=workspace.ticket.ticket_id,
        order_id=workspace.order_data.order_id,
        issue_type=workspace.intent.issue_type.value,
        ai_draft=ai_draft,
        human_final=human_final,
        hitl_action=decision.action.value,
        human_agent_id=decision.human_agent_id,
        sop_citation=workspace.sop_match.citation,
        was_edited=decision.action == HITLAction.EDIT_AND_APPROVE,
        edit_diff_chars=edit_dist,
        processing_time_ms=elapsed,
    )
