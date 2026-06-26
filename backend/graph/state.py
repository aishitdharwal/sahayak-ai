"""
Graph State Definition

DESIGN DECISION: TypedDict over Pydantic for graph state.

LangGraph's reducer system (used for merging parallel node outputs) works
natively with TypedDict. Pydantic adds validation overhead on every state
transition. We use Pydantic only at node boundaries for structured LLM output.

The state is serialized by SqliteSaver at every node transition, so every
field must be JSON-serializable.
"""

from typing import Optional
from typing_extensions import TypedDict
from backend.models.ticket import (
    InboundTicket,
    ExtractedIntent,
    SOPMatch,
    OrderData,
    AgentWorkspace,
    HITLDecision,
)
from backend.models.audit import AuditLogEntry


class AgentState(TypedDict):
    # The raw inbound ticket — set once at entry, never mutated
    ticket: InboundTicket

    # Outputs from each pipeline node — built up as the graph runs
    intent: Optional[ExtractedIntent]
    sop_match: Optional[SOPMatch]
    order_data: Optional[OrderData]

    # The assembled workspace handed to the human agent
    workspace: Optional[AgentWorkspace]

    # Injected by the HITL resume — this is what unblocks the graph
    hitl_decision: Optional[HITLDecision]

    # Written by execute_action after the HITL gate clears
    audit_entry: Optional[AuditLogEntry]

    # Tracks graph processing metadata
    pipeline_start_ms: Optional[int]
    error: Optional[str]
