import { useState, useCallback } from "react";
import axios from "axios";
import { AgentWorkspace, HITLAction, WSEvent } from "../types";
import { TicketCard } from "../components/TicketCard";
import { AIInterpretation } from "../components/AIInterpretation";
import { SOPCitation } from "../components/SOPCitation";
import { DraftEditor } from "../components/DraftEditor";
import { ActionButtons } from "../components/ActionButtons";
import { useAgentSocket } from "../hooks/useAgentSocket";

const API = "http://localhost:8000";
const AGENT_ID = "agent-001";

type TicketState =
  | { status: "idle" }
  | { status: "processing"; ticket_id: string }
  | { status: "review"; workspace: AgentWorkspace }
  | { status: "resolved"; ticket_id: string; action: HITLAction }
  | { status: "error"; message: string };

export function AgentDashboard() {
  const [ticketState, setTicketState] = useState<TicketState>({ status: "idle" });
  const [editedDraft, setEditedDraft] = useState<string>("");
  const [connectionStatus, setConnectionStatus] = useState<"connecting" | "live">("connecting");

  const handleWSEvent = useCallback((event: WSEvent) => {
    setConnectionStatus("live");

    if (event.event === "review_ready") {
      setEditedDraft(event.workspace.draft_response);
      setTicketState({ status: "review", workspace: event.workspace });
    } else if (event.event === "ticket_resolved") {
      setTicketState({ status: "resolved", ticket_id: event.ticket_id, action: event.action });
    } else if (event.event === "pipeline_error") {
      setTicketState({ status: "error", message: event.error });
    }
  }, []);

  useAgentSocket(handleWSEvent);

  const handleDecision = async (action: HITLAction, notes?: string) => {
    if (ticketState.status !== "review") return;
    const { workspace } = ticketState;

    const isEdited = editedDraft !== workspace.draft_response;

    await axios.post(`${API}/api/hitl/${workspace.ticket.ticket_id}/decide`, {
      ticket_id: workspace.ticket.ticket_id,
      action: isEdited ? "edit_and_approve" : action,
      final_response: editedDraft,
      human_agent_id: AGENT_ID,
      edit_notes: notes,
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">
            स
          </div>
          <div>
            <h1 className="font-bold text-gray-900">Sahayak AI</h1>
            <p className="text-xs text-gray-500">Agent Assist Workspace</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connectionStatus === "live" ? "bg-green-500" : "bg-yellow-400 animate-pulse"}`} />
          <span className="text-xs text-gray-500">{connectionStatus === "live" ? "Live" : "Connecting..."}</span>
          <span className="text-xs text-gray-400 ml-3">Agent: {AGENT_ID}</span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">

        {/* IDLE — waiting for a ticket */}
        {ticketState.status === "idle" && (
          <div className="flex flex-col items-center justify-center h-80 text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center text-3xl mb-4">⏳</div>
            <h2 className="text-lg font-semibold text-gray-700 mb-1">Waiting for tickets</h2>
            <p className="text-sm text-gray-400">New customer tickets will appear here automatically.</p>
          </div>
        )}

        {/* PROCESSING — pipeline running */}
        {ticketState.status === "processing" && (
          <div className="flex flex-col items-center justify-center h-80 text-center">
            <div className="w-16 h-16 bg-indigo-50 rounded-2xl flex items-center justify-center text-3xl mb-4 animate-pulse">🤖</div>
            <h2 className="text-lg font-semibold text-gray-700 mb-1">AI pipeline running...</h2>
            <p className="text-sm text-gray-400">Parsing intent → Retrieving SOP → Querying OMS</p>
            <p className="text-xs text-gray-300 mt-1">Ticket: {ticketState.ticket_id}</p>
          </div>
        )}

        {/* ERROR */}
        {ticketState.status === "error" && (
          <div className="flex flex-col items-center justify-center h-80 text-center">
            <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center text-3xl mb-4">⚠️</div>
            <h2 className="text-lg font-semibold text-red-700 mb-1">Pipeline Error</h2>
            <p className="text-sm text-gray-500">{ticketState.message}</p>
          </div>
        )}

        {/* RESOLVED */}
        {ticketState.status === "resolved" && (
          <div className="flex flex-col items-center justify-center h-80 text-center">
            <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center text-3xl mb-4">✅</div>
            <h2 className="text-lg font-semibold text-gray-700 mb-1">Ticket Resolved</h2>
            <p className="text-sm text-gray-500">Action: <span className="font-semibold capitalize">{ticketState.action.replace("_", " ")}</span></p>
            <p className="text-xs text-gray-400 mt-1">Ticket: {ticketState.ticket_id}</p>
            <button
              onClick={() => setTicketState({ status: "idle" })}
              className="mt-4 text-sm text-indigo-600 hover:underline"
            >
              Ready for next ticket
            </button>
          </div>
        )}

        {/* REVIEW — the main HITL workspace */}
        {ticketState.status === "review" && (() => {
          const { workspace } = ticketState;
          const isEdited = editedDraft !== workspace.draft_response;

          return (
            <div>
              {/* Pipeline breadcrumb */}
              <div className="flex items-center gap-2 mb-5 text-xs text-gray-400">
                <span className="text-green-600 font-semibold">✓ Intent Parsed</span>
                <span>→</span>
                <span className="text-green-600 font-semibold">✓ SOP Retrieved</span>
                <span>→</span>
                <span className="text-green-600 font-semibold">✓ OMS Queried</span>
                <span>→</span>
                <span className="text-amber-600 font-bold animate-pulse">⛔ Awaiting Your Review</span>
              </div>

              <div className="grid grid-cols-12 gap-5">
                {/* Left column: ticket + AI interpretation */}
                <div className="col-span-4 space-y-4">
                  <TicketCard ticket={workspace.ticket} intent={workspace.intent} />
                  <AIInterpretation
                    intent={workspace.intent}
                    orderData={workspace.order_data}
                    confidenceOverall={workspace.confidence_overall}
                  />
                </div>

                {/* Center column: SOP + Draft */}
                <div className="col-span-5 space-y-4">
                  <SOPCitation sop={workspace.sop_match} />
                  <DraftEditor
                    initialDraft={workspace.draft_response}
                    onChange={setEditedDraft}
                  />
                </div>

                {/* Right column: decision */}
                <div className="col-span-3">
                  <ActionButtons
                    ticketId={workspace.ticket.ticket_id}
                    finalResponse={editedDraft}
                    isEdited={isEdited}
                    onDecision={handleDecision}
                  />
                </div>
              </div>
            </div>
          );
        })()}
      </main>
    </div>
  );
}
