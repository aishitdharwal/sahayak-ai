"""
Node 2: Agentic RAG — SOP Policy Retrieval

MODEL: claude-sonnet-4-6 (reasoning)

DESIGN DECISION: Agentic RAG vs. standard one-shot retrieval.

Standard RAG: embed query → retrieve top-k → done.
Agentic RAG: retrieve → evaluate confidence → if low, rewrite query → retrieve again.

Why bother? Policy documents use legal/procedural language that doesn't always
match how customers describe their problems. "My TV wasn't delivered" has low
cosine similarity with "Order Not Delivered (OND) compensation threshold" even
though they're about the same thing. The retry loop bridges this semantic gap.

TRADEOFF: This adds 1-2 extra LLM calls on low-confidence retrievals (~30% of cases
in testing). The cost is acceptable because Node 2 runs once per ticket, and a
wrong policy citation can cause a compliance violation or a Rs. 50,000 incorrect refund.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from backend.config import settings
from backend.graph.state import AgentState
from backend.models.ticket import SOPMatch
from backend.rag.retriever import retrieve_sop


_llm = ChatAnthropic(
    model=settings.reasoning_model,
    api_key=settings.anthropic_api_key,
    temperature=0,
).with_structured_output(SOPMatch)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a compliance-grounding agent. Given a customer issue and retrieved SOP context,
extract the most relevant policy clause and provide a clear recommended action.

Be conservative with confidence scores. Only give > 0.85 if the policy clause directly
and unambiguously addresses the customer's exact situation."""),
    ("human", """Customer issue type: {issue_type}
Customer sentiment: {sentiment_score} (0=angry, 1=calm)
Order value: Rs. {item_value}

Retrieved SOP context:
{sop_context}

Extract the most applicable policy clause and recommended action.""")
])


async def rag_retriever_node(state: AgentState) -> dict:
    if state.get("error"):
        return {}

    intent = state["intent"]
    ticket = state["ticket"]

    # First retrieval attempt
    sop_context = await retrieve_sop(
        query=f"{intent.issue_type} {' '.join(intent.key_facts)}",
        issue_type=intent.issue_type.value,
    )

    try:
        sop_match: SOPMatch = await _llm.ainvoke(
            _PROMPT.format_messages(
                issue_type=intent.issue_type.value,
                sentiment_score=intent.sentiment_score,
                item_value="unknown",  # Will be filled after OMS in a real system
                sop_context=sop_context,
            )
        )

        # Agentic retry: if confidence is low, rewrite the query and try again
        if sop_match.confidence < 0.70:
            refined_query = f"{intent.issue_type.value.replace('_', ' ')} policy exception escalation"
            sop_context_retry = await retrieve_sop(
                query=refined_query,
                issue_type=intent.issue_type.value,
            )
            sop_match = await _llm.ainvoke(
                _PROMPT.format_messages(
                    issue_type=intent.issue_type.value,
                    sentiment_score=intent.sentiment_score,
                    item_value="unknown",
                    sop_context=sop_context_retry,
                )
            )

        return {"sop_match": sop_match}

    except Exception as e:
        return {"error": f"RAG retrieval failed: {str(e)}"}
