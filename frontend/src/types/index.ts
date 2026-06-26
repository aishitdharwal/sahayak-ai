export type IssueType =
  | "order_not_delivered"
  | "wrong_item"
  | "damaged_item"
  | "return_request"
  | "refund_delayed"
  | "other";

export type UrgencyLevel = "low" | "medium" | "high";
export type HITLAction = "approve" | "edit_and_approve" | "reject";

export interface InboundTicket {
  ticket_id: string;
  customer_name: string;
  customer_email: string;
  customer_id: string;
  order_id: string;
  raw_text: string;
  channel: string;
  created_at: string;
}

export interface ExtractedIntent {
  order_id: string;
  customer_id: string;
  issue_type: IssueType;
  sentiment_score: number;
  urgency: UrgencyLevel;
  key_facts: string[];
  requires_escalation: boolean;
}

export interface SOPMatch {
  clause_text: string;
  policy_section: string;
  confidence: number;
  recommended_action: string;
  citation: string;
}

export interface OrderData {
  order_id: string;
  order_status: string;
  item_name: string;
  item_value: number;
  payment_method: string;
  order_date: string;
  delivery_date?: string;
  return_window_days: number;
  days_since_delivery?: number;
  return_eligible: boolean;
  previous_refund_processed: boolean;
  carrier_confirmation?: string;
}

export interface AgentWorkspace {
  ticket: InboundTicket;
  intent: ExtractedIntent;
  sop_match: SOPMatch;
  order_data: OrderData;
  draft_response: string;
  confidence_overall: number;
}

export interface HITLDecision {
  ticket_id: string;
  action: HITLAction;
  final_response: string;
  human_agent_id: string;
  edit_notes?: string;
}

// WebSocket event types
export type WSEvent =
  | { event: "review_ready"; ticket_id: string; workspace: AgentWorkspace }
  | { event: "ticket_resolved"; ticket_id: string; action: HITLAction; human_agent_id: string }
  | { event: "pipeline_error"; ticket_id: string; error: string };
