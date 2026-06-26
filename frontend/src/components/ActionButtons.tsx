import { useState } from "react";
import { HITLAction } from "../types";

interface Props {
  ticketId: string;
  finalResponse: string;
  isEdited: boolean;
  onDecision: (action: HITLAction, notes?: string) => Promise<void>;
}

export function ActionButtons({ ticketId, finalResponse, isEdited, onDecision }: Props) {
  const [loading, setLoading] = useState<HITLAction | null>(null);
  const [rejectNotes, setRejectNotes] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const handle = async (action: HITLAction, notes?: string) => {
    setLoading(action);
    try {
      await onDecision(action, notes);
    } finally {
      setLoading(null);
    }
  };

  if (showRejectForm) {
    return (
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-5">
        <h4 className="font-semibold text-gray-900 text-sm mb-2">Reason for rejection</h4>
        <textarea
          className="w-full h-20 text-sm bg-gray-50 border border-gray-200 rounded-lg p-2 resize-none focus:outline-none focus:ring-2 focus:ring-red-300 mb-3"
          placeholder="Note for audit log (optional)..."
          value={rejectNotes}
          onChange={(e) => setRejectNotes(e.target.value)}
        />
        <div className="flex gap-2">
          <button
            onClick={() => handle("reject", rejectNotes)}
            disabled={loading === "reject"}
            className="flex-1 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold py-2.5 px-4 rounded-lg text-sm transition-colors"
          >
            {loading === "reject" ? "Rejecting..." : "Confirm Reject"}
          </button>
          <button
            onClick={() => setShowRejectForm(false)}
            className="px-4 py-2.5 border border-gray-200 text-gray-600 rounded-lg text-sm hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide mb-4">
        Your Decision
      </h3>

      <div className="space-y-3">
        <button
          onClick={() => handle(isEdited ? "edit_and_approve" : "approve")}
          disabled={loading !== null}
          className="w-full bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-bold py-3 px-4 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
        >
          {loading === "approve" || loading === "edit_and_approve" ? (
            <span className="animate-spin">⟳</span>
          ) : (
            <span>✓</span>
          )}
          {isEdited ? "Approve Edited Response" : "Approve & Send"}
        </button>

        <button
          onClick={() => setShowRejectForm(true)}
          disabled={loading !== null}
          className="w-full bg-white hover:bg-red-50 disabled:opacity-50 text-red-600 font-semibold py-3 px-4 rounded-xl text-sm border-2 border-red-200 transition-colors"
        >
          ✕ Reject — Route to Manual Queue
        </button>
      </div>

      <p className="text-xs text-gray-400 mt-3 text-center">
        Every decision is audit-logged with your agent ID and timestamp.
      </p>
    </div>
  );
}
