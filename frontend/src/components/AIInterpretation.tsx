import { ExtractedIntent, OrderData } from "../types";

interface Props {
  intent: ExtractedIntent;
  orderData: OrderData;
  confidenceOverall: number;
}

const ISSUE_LABELS: Record<string, string> = {
  order_not_delivered: "Order Not Delivered",
  wrong_item: "Wrong Item Delivered",
  damaged_item: "Damaged Item",
  return_request: "Return Request",
  refund_delayed: "Refund Delayed",
  other: "Other",
};

const confidenceColor = (c: number) => {
  if (c >= 0.8) return "text-green-700 bg-green-50 border-green-200";
  if (c >= 0.6) return "text-yellow-700 bg-yellow-50 border-yellow-200";
  return "text-red-700 bg-red-50 border-red-200";
};

export function AIInterpretation({ intent, orderData, confidenceOverall }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">
          AI Interpretation
        </h3>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${confidenceColor(confidenceOverall)}`}>
          {(confidenceOverall * 100).toFixed(0)}% confidence
        </span>
      </div>

      {/* Issue classification */}
      <div className="mb-4">
        <p className="text-xs text-gray-500 mb-1">Issue Type</p>
        <p className="font-semibold text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg inline-block text-sm">
          {ISSUE_LABELS[intent.issue_type]}
        </p>
      </div>

      {/* Extracted entities */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Item</p>
          <p className="text-sm font-medium text-gray-800">{orderData.item_name}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Order Value</p>
          <p className="text-sm font-medium text-gray-800">₹{orderData.item_value.toLocaleString("en-IN")}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Order Status</p>
          <p className="text-sm font-medium text-gray-800">{orderData.order_status}</p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Return Eligible</p>
          <p className={`text-sm font-bold ${orderData.return_eligible ? "text-green-600" : "text-red-600"}`}>
            {orderData.return_eligible ? "Yes" : `No — ${orderData.days_since_delivery}d / ${orderData.return_window_days}d window`}
          </p>
        </div>
      </div>

      {/* Carrier note if present */}
      {orderData.carrier_confirmation && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
          <p className="text-xs font-semibold text-orange-700 mb-0.5">Carrier Note</p>
          <p className="text-xs text-orange-600">{orderData.carrier_confirmation}</p>
        </div>
      )}

      {/* Key facts */}
      <div>
        <p className="text-xs text-gray-500 mb-2">Key Facts Extracted</p>
        <ul className="space-y-1.5">
          {intent.key_facts.map((fact, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
              <span className="text-indigo-400 mt-0.5 flex-shrink-0">•</span>
              {fact}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
