import { InboundTicket, ExtractedIntent, UrgencyLevel } from "../types";

interface Props {
  ticket: InboundTicket;
  intent: ExtractedIntent;
}

const URGENCY_COLORS: Record<UrgencyLevel, string> = {
  high: "bg-red-100 text-red-800 border-red-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-green-100 text-green-800 border-green-200",
};

const SENTIMENT_LABEL = (score: number) => {
  if (score < 0.3) return { label: "Very Distressed", color: "text-red-600" };
  if (score < 0.6) return { label: "Frustrated", color: "text-orange-500" };
  return { label: "Calm", color: "text-green-600" };
};

export function TicketCard({ ticket, intent }: Props) {
  const sentiment = SENTIMENT_LABEL(intent.sentiment_score);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <h2 className="font-semibold text-gray-900">{ticket.customer_name}</h2>
          <p className="text-sm text-gray-500">{ticket.customer_email}</p>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${URGENCY_COLORS[intent.urgency]}`}>
          {intent.urgency.toUpperCase()}
        </span>
      </div>

      <div className="flex gap-3 mb-4 text-sm">
        <span className="text-gray-500">Order: <span className="font-mono font-medium text-gray-800">{ticket.order_id}</span></span>
        <span className="text-gray-300">|</span>
        <span className="text-gray-500">Via: <span className="font-medium text-gray-700 capitalize">{ticket.channel}</span></span>
      </div>

      <div className="bg-gray-50 rounded-lg p-3 mb-4">
        <p className="text-sm text-gray-700 leading-relaxed italic">"{ticket.raw_text}"</p>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">Sentiment:</span>
          <span className={`text-xs font-semibold ${sentiment.color}`}>{sentiment.label}</span>
          <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-red-500 via-yellow-400 to-green-500 rounded-full"
              style={{ width: `${intent.sentiment_score * 100}%` }}
            />
          </div>
          <span className="text-xs text-gray-400">{(intent.sentiment_score * 100).toFixed(0)}%</span>
        </div>

        {intent.requires_escalation && (
          <span className="text-xs font-bold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">
            ⚠ Escalation Flag
          </span>
        )}
      </div>
    </div>
  );
}
