"""
Sahayak AI — LangGraph Pipeline

This is the architectural centrepiece. Read this file carefully.

THE GRAPH TOPOLOGY:
    intent_parser → rag_retriever → tool_matcher → [INTERRUPT] → execute_action

THE HITL MECHANISM:
    We use interrupt_before=["execute_action"].

    This means the graph runs the first three nodes, serializes its state via
    SqliteSaver, and then STOPS. The execute_action node never runs until a human
    explicitly resumes the thread by calling graph.invoke(None, config) after
    injecting their HITLDecision into state.

DESIGN DECISION: interrupt_before vs. interrupt_after

    interrupt_before=["execute_action"]:
        Graph pauses BEFORE execute_action runs.
        At the moment of pause, NO external state has been mutated.
        Human sees the proposed action before it happens.
        ✓ Correct for HITL — human reviews, then execution happens.

    interrupt_after=["tool_matcher"]:
        Functionally identical for this use case but semantically less clear.
        "Interrupt before the dangerous node" is more legible than
        "interrupt after the safe node."

DESIGN DECISION: SqliteSaver for checkpoint persistence.

    SqliteSaver stores graph state (including all node outputs) to a SQLite file.
    This means:
    - If the server restarts between a ticket arriving and the human approving,
      the state is not lost. The human can resume from where it stopped.
    - Each ticket gets its own thread_id (= ticket_id), so N concurrent tickets
      can all be in-flight simultaneously.

    For production: swap SqliteSaver → PostgresSaver. One config line change.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.graph.state import AgentState
from backend.graph.nodes.intent_parser import intent_parser_node
from backend.graph.nodes.rag_retriever import rag_retriever_node
from backend.graph.nodes.tool_matcher import tool_matcher_node
from backend.graph.nodes.execute_action import execute_action_node
from backend.config import settings


def build_graph(checkpointer: SqliteSaver) -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("intent_parser", intent_parser_node)
    workflow.add_node("rag_retriever", rag_retriever_node)
    workflow.add_node("tool_matcher", tool_matcher_node)
    workflow.add_node("execute_action", execute_action_node)

    workflow.set_entry_point("intent_parser")
    workflow.add_edge("intent_parser", "rag_retriever")
    workflow.add_edge("rag_retriever", "tool_matcher")
    workflow.add_edge("tool_matcher", "execute_action")
    workflow.add_edge("execute_action", END)

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"],
    )


def get_thread_config(ticket_id: str) -> dict:
    """Each ticket runs as an isolated thread. Thread ID = Ticket ID."""
    return {"configurable": {"thread_id": ticket_id}}
