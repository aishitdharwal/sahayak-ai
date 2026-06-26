"""
OMS Tool Definitions — Read-Only

DESIGN DECISION: Blast Radius Insulation

These tools are ALL read-only. The agent can fetch any information it needs
to make a recommendation, but it cannot trigger any state mutation (refund,
return initiation, order cancellation) directly.

Mutations only happen in the execute_action node, AFTER the human agent
has reviewed and approved the AgentWorkspace. This means even a fully
jailbroken or hallucinating LLM cannot accidentally issue a Rs. 50,000
refund or cancel an order. The blast radius of a model failure is zero.

In production, these would call a read-only DB replica or a dedicated
internal read API with scoped IAM credentials.
"""

from langchain_core.tools import tool
from backend.graph.tools.mock_data import MOCK_ORDERS
from backend.models.ticket import OrderData


@tool
def get_order_status(order_id: str) -> dict:
    """Fetch order metadata and current status from the OMS."""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found in system."}
    return order


@tool
def check_return_eligibility(order_id: str) -> dict:
    """Check if an order is within its return window and eligible for return."""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found."}
    return {
        "order_id": order_id,
        "return_eligible": order["return_eligible"],
        "return_window_days": order["return_window_days"],
        "days_since_delivery": order["days_since_delivery"],
        "days_over_window": max(
            0, (order["days_since_delivery"] or 0) - order["return_window_days"]
        ),
    }


@tool
def get_refund_estimate(order_id: str) -> dict:
    """Calculate the refund amount the customer would receive."""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"error": f"Order {order_id} not found."}
    return {
        "order_id": order_id,
        "item_value": order["item_value"],
        "payment_method": order["payment_method"],
        "previous_refund_processed": order["previous_refund_processed"],
        "estimated_refund_amount": order["item_value"] if not order["previous_refund_processed"] else 0,
        "refund_note": "Full refund applicable" if not order["previous_refund_processed"] else "Refund already processed",
    }


# The list of tools available to Node 3 (Tool Matcher)
OMS_READ_TOOLS = [get_order_status, check_return_eligibility, get_refund_estimate]
