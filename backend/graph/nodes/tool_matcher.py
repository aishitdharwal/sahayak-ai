"""
Node 3: Tool Matcher — OMS Query + Workspace Assembly

MODEL: claude-sonnet-4-6 (reasoning)

This node has two responsibilities:
1. Query the OMS read tools to get live order data.
2. Assemble the AgentWorkspace — the final package the human agent reviews.

DESIGN DECISION: Why assemble the workspace HERE rather than in a separate node?
Because workspace assembly requires comparing the live order data against the
retrieved SOP policy to produce the draft response. That cross-referencing is a
reasoning task, not just a data join. Combining them in one node reduces the
state we need to pass between nodes and keeps the prompt coherent.

The draft response is a SUGGESTION. The human will always review it.
This is the Generator-Verifier Gap in action: generating the draft takes ~3s,
reviewing and correcting it takes the human ~10-15s. Without AI, writing the
full response from scratch takes ~3-4 minutes.
"""

import json
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from backend.config import settings
from backend.graph.state import AgentState
from backend.models.ticket import AgentWorkspace, OrderData
from backend.graph.tools.oms_tools import OMS_READ_TOOLS
from backend.graph.tools.mock_data import MOCK_ORDERS


_llm = ChatAnthropic(
    model=settings.reasoning_model,
    api_key=settings.anthropic_api_key,
    temperature=0.1,  # Slight warmth for response drafting — purely deterministic drafts feel robotic
)

_DRAFT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are drafting a customer support response on behalf of a human agent.
The human agent will review, edit if needed, and approve before this is sent.

Tone guidelines based on sentiment score:
- Score < 0.3: Lead with empathy. Do NOT start with policy.
- Score 0.3-0.7: Balanced, professional.
- Score > 0.7: Efficient and warm.

CRITICAL: Do not mention specific refund amounts unless you are certain from order data.
Write [REFUND_AMOUNT] as a placeholder if uncertain.
Do not promise escalation resolution timelines you cannot confirm.
Keep the draft under 150 words."""),
    ("human", """Customer: {customer_name}
Issue type: {issue_type}
Sentiment: {sentiment_score}
Key facts: {key_facts}

Order data:
{order_data}

Policy guidance:
{recommended_action} ({citation})

Draft the response.""")
])


async def tool_matcher_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}

    intent = state["intent"]
    sop_match = state["sop_match"]
    ticket = state["ticket"]

    # Fetch order data from OMS (read-only)
    raw_order = MOCK_ORDERS.get(ticket.order_id, {})
    if not raw_order:
        return {"error": f"Order {ticket.order_id} not found in OMS."}

    order_data = OrderData(**raw_order)

    # Draft the response using order data + SOP guidance
    draft_msg = await _llm.ainvoke(
        _DRAFT_PROMPT.format_messages(
            customer_name=ticket.customer_name,
            issue_type=intent.issue_type.value,
            sentiment_score=intent.sentiment_score,
            key_facts=", ".join(intent.key_facts),
            order_data=json.dumps(raw_order, indent=2),
            recommended_action=sop_match.recommended_action,
            citation=sop_match.citation,
        )
    )
    draft_response = draft_msg.content

    # Overall confidence = average of intent certainty (proxy: not other) + SOP confidence
    intent_confidence = 0.9 if intent.issue_type.value != "other" else 0.5
    overall_confidence = (intent_confidence + sop_match.confidence) / 2

    workspace = AgentWorkspace(
        ticket=ticket,
        intent=intent,
        sop_match=sop_match,
        order_data=order_data,
        draft_response=draft_response,
        confidence_overall=overall_confidence,
    )

    return {"workspace": workspace, "order_data": order_data}
