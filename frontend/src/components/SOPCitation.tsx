import { SOPMatch } from "../types";

interface Props {
  sop: SOPMatch;
}

const confidenceBar = (c: number) => {
  if (c >= 0.8) return "bg-green-500";
  if (c >= 0.6) return "bg-yellow-500";
  return "bg-red-400";
};

export function SOPCitation({ sop }: Props) {
  return (
    <div className="bg-white rounded-xl border border-amber-200 shadow-sm p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-amber-500 text-base">📋</span>
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">
          Policy Grounding
        </h3>
      </div>

      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded">
            {sop.citation}
          </span>
          <div className="flex items-center gap-1.5">
            <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${confidenceBar(sop.confidence)}`}
                style={{ width: `${sop.confidence * 100}%` }}
              />
            </div>
            <span className="text-xs text-gray-400">{(sop.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
        <p className="text-xs text-gray-500">{sop.policy_section}</p>
      </div>

      {/* The exact retrieved policy clause */}
      <blockquote className="border-l-4 border-amber-400 bg-amber-50 pl-3 py-2 pr-2 rounded-r-lg mb-3">
        <p className="text-sm text-gray-700 leading-relaxed">{sop.clause_text}</p>
      </blockquote>

      {/* What the AI recommends the agent should do */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <p className="text-xs font-semibold text-blue-700 mb-1">Recommended Action</p>
        <p className="text-sm text-blue-800">{sop.recommended_action}</p>
      </div>
    </div>
  );
}
