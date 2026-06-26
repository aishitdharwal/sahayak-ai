from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class IssueType(str, Enum):
    ORDER_NOT_DELIVERED = "order_not_delivered"
    WRONG_ITEM = "wrong_item"
    DAMAGED_ITEM = "damaged_item"
    RETURN_REQUEST = "return_request"
    REFUND_DELAYED = "refund_delayed"
    OTHER = "other"


class UrgencyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class HITLAction(str, Enum):
    APPROVE = "approve"
    EDIT_AND_APPROVE = "edit_and_approve"
    REJECT = "reject"


# --- Inbound ticket (raw, as it arrives from the customer) ---

class InboundTicket(BaseModel):
    ticket_id: str
    customer_name: str
    customer_email: str
    customer_id: str
    order_id: str
    raw_text: str
    channel: str = "email"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Node 1 output: structured extraction from raw ticket text ---
# TRADEOFF: Strict Pydantic schema here rather than a free-form dict.
# This forces the LLM into a typed contract. Any downstream node can rely on
# these fields being present and correctly typed. The cost: the LLM prompt
# must include the schema, adding ~200 tokens per call.

class ExtractedIntent(BaseModel):
    order_id: str = Field(description="Order ID mentioned in the ticket")
    customer_id: str = Field(description="Customer ID from ticket metadata")
    issue_type: IssueType = Field(description="Classified issue category")
    sentiment_score: float = Field(
        ge=0.0, le=1.0,
        description="Customer sentiment: 0.0 = very angry, 1.0 = calm/positive"
    )
    urgency: UrgencyLevel = Field(description="Inferred urgency of the request")
    key_facts: list[str] = Field(
        description="2-4 bullet point facts extracted from the ticket text",
        max_length=4
    )
    requires_escalation: bool = Field(
        description="True if this ticket matches any immediate escalation trigger"
    )


# --- Node 2 output: SOP policy grounding ---

class SOPMatch(BaseModel):
    clause_text: str = Field(description="Exact policy clause retrieved")
    policy_section: str = Field(description="Section name, e.g. 'Return Policy § 3.2'")
    confidence: float = Field(ge=0.0, le=1.0, description="Retrieval confidence score")
    recommended_action: str = Field(description="What the policy says the agent should do")
    citation: str = Field(description="Human-readable citation, e.g. 'Return Policy, Section 3.2'")


# --- Node 3 output: live order data from OMS tools ---

class OrderData(BaseModel):
    order_id: str
    order_status: str
    item_name: str
    item_value: float
    payment_method: str
    order_date: str
    delivery_date: Optional[str] = None
    return_window_days: int
    days_since_delivery: Optional[int] = None
    return_eligible: bool
    previous_refund_processed: bool = False
    carrier_confirmation: Optional[str] = None


# --- The assembled workspace shown to the human agent ---
# This is what the human sees on the dashboard before approving.

class AgentWorkspace(BaseModel):
    ticket: InboundTicket
    intent: ExtractedIntent
    sop_match: SOPMatch
    order_data: OrderData
    draft_response: str = Field(description="AI-generated response draft for the human to review")
    confidence_overall: float = Field(ge=0.0, le=1.0)


# --- Human's decision on the workspace ---

class HITLDecision(BaseModel):
    ticket_id: str
    action: HITLAction
    final_response: str = Field(description="The approved (possibly edited) response text")
    human_agent_id: str = "agent-001"
    reviewed_at: datetime = Field(default_factory=datetime.utcnow)
    edit_notes: Optional[str] = None
