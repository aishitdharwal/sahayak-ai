import { useEffect, useState } from "react";
import axios from "axios";

interface QueueTicket {
  ticket_id: string;
  customer_name: string;
  order_id: string;
  status: string;
  created_at: string;
}

const API = "http://localhost:8000";

export function TicketQueue() {
  const [tickets, setTickets] = useState<QueueTicket[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchQueue = async () => {
    try {
      const res = await axios.get(`${API}/api/tickets/queue`);
      setTickets(res.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    const interval = setInterval(fetchQueue, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold text-sm">स</div>
          <h1 className="text-xl font-bold text-gray-900">Ticket Queue</h1>
          <span className="ml-auto text-xs text-gray-400 bg-gray-100 px-2.5 py-1 rounded-full">
            {tickets.length} awaiting review
          </span>
        </div>

        {loading ? (
          <div className="text-center text-gray-400 py-12">Loading queue...</div>
        ) : tickets.length === 0 ? (
          <div className="text-center text-gray-400 py-12">No tickets awaiting review.</div>
        ) : (
          <div className="space-y-3">
            {tickets.map((t) => (
              <div key={t.ticket_id} className="bg-white rounded-xl border border-amber-200 p-4 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{t.customer_name}</p>
                  <p className="text-sm text-gray-500">Order: <span className="font-mono">{t.order_id}</span></p>
                  <p className="text-xs text-gray-400 mt-0.5">Arrived: {new Date(t.created_at).toLocaleTimeString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-1 rounded-full font-semibold">
                    Awaiting Review
                  </span>
                  <span className="text-xs font-mono text-gray-400">{t.ticket_id}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
