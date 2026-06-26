"""
Node 1: Intent Parser & Entity Extractor

MODEL: claude-haiku-4-5 (cheap, fast)

DESIGN DECISION: Cheapest capable model for a deterministic extraction task.
Intent classification and entity extraction don't require deep reasoning —
they require consistent structured output from a clear schema. Haiku does this
at ~20x lower cost than Sonnet. Reserve Sonnet's budget for policy interpretation
in Node 2, where actual reasoning matters.

OUTPUT CONTRACT: Always returns ExtractedIntent or sets state["error"].
Downstream nodes can assume these fields exist if error is None.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from backend.config import settings
from backend.graph.state import AgentState
from backend.models.ticket import ExtractedIntent


_llm = ChatAnthropic(
    model=settings.intent_model,
    api_key=settings.anthropic_api_key,
    temperature=0,  # Deterministic — we want consistent classification, not creativity
).with_structured_output(ExtractedIntent)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a customer support triage agent for an e-commerce platform.
Extract structured information from the customer ticket below.

Be precise with sentiment_score: 0.0 = extremely angry/distressed, 1.0 = calm/polite.
For requires_escalation, check if the ticket mentions: legal threats, consumer court,
social media threats, orders above Rs. 50,000, or if the customer has contacted 3+ times."""),
    ("human", """Customer ticket:
Name: {customer_name}
Order ID: {order_id}
Message: {raw_text}

Extract the structured intent.""")
])


async def intent_parser_node(state: AgentState) -> dict:
    ticket = state["ticket"]
    try:
        intent: ExtractedIntent = await _llm.ainvoke(
            _PROMPT.format_messages(
                customer_name=ticket.customer_name,
                order_id=ticket.order_id,
                raw_text=ticket.raw_text,
            )
        )
        return {"intent": intent}
    except Exception as e:
        return {"error": f"Intent parsing failed: {str(e)}"}
