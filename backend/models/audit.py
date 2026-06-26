from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    """
    Every HITL decision is logged immutably here.

    TRADEOFF: Storing both the AI draft and the human's final response lets you
    compute the 'edit distance' over time — which is your ground truth for measuring
    how well the AI is performing and whether prompts are drifting.
    This is what Flipkart calls their 'grounding fidelity' metric.
    """
    log_id: str
    ticket_id: str
    order_id: str
    issue_type: str
    ai_draft: str
    human_final: str
    hitl_action: str
    human_agent_id: str
    sop_citation: str
    was_edited: bool
    edit_diff_chars: int = Field(description="Character-level distance between AI draft and final")
    processing_time_ms: int = Field(description="Total pipeline time before HITL gate opened")
    created_at: datetime = Field(default_factory=datetime.utcnow)
