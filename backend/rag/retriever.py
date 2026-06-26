"""
SOP Retriever — used by Node 2 (rag_retriever_node)

DESIGN DECISION: Issue-type metadata filtering + semantic search.

Pure semantic search over all documents works but retrieves noisy results —
an "order not delivered" query might pull in refund timeline chunks when the
most relevant section is the OND compensation policy.

Metadata filtering (issue_type → section keywords) pre-narrows the search space.
This is called "hybrid metadata+semantic retrieval" and it's standard in production.
"""

from functools import lru_cache
from backend.rag.indexer import get_vectorstore

# Maps issue types to section keywords that should be prioritized in retrieval
ISSUE_TO_SECTION_HINTS: dict[str, list[str]] = {
    "order_not_delivered": ["order not delivered", "OND", "carrier", "refund full"],
    "wrong_item": ["wrong item", "wrong item delivered", "exchange", "replacement"],
    "damaged_item": ["damaged", "arrival", "photographic evidence", "replacement"],
    "return_request": ["return", "return window", "return eligibility", "late return"],
    "refund_delayed": ["refund timeline", "delayed refund", "compensation", "payment method"],
    "other": ["escalation", "escalate"],
}


@lru_cache(maxsize=1)
def _get_retriever():
    """Cache the vectorstore — ChromaDB init is slow, do it once."""
    vs = get_vectorstore()
    return vs.as_retriever(search_kwargs={"k": 4})


async def retrieve_sop(query: str, issue_type: str) -> str:
    """
    Retrieve relevant SOP chunks and format them as context for the LLM.
    Returns a single string block ready to be injected into the prompt.
    """
    hints = ISSUE_TO_SECTION_HINTS.get(issue_type, [])
    enriched_query = f"{query} {' '.join(hints)}"

    retriever = _get_retriever()
    docs = retriever.invoke(enriched_query)

    if not docs:
        return "No relevant SOP sections found. Escalate to Tier 2."

    context_parts = []
    for i, doc in enumerate(docs, 1):
        section = doc.metadata.get("section", "General")
        document = doc.metadata.get("document", "SOP")
        context_parts.append(f"[{i}] {document} — {section}\n{doc.page_content}")

    return "\n\n---\n\n".join(context_parts)
