import { useState } from "react";

interface Props {
  initialDraft: string;
  onChange: (text: string) => void;
}

export function DraftEditor({ initialDraft, onChange }: Props) {
  const [text, setText] = useState(initialDraft);
  const [isEditing, setIsEditing] = useState(false);
  const charDiff = text.length - initialDraft.length;

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    onChange(e.target.value);
    setIsEditing(e.target.value !== initialDraft);
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-900 text-sm uppercase tracking-wide">
          Response Draft
        </h3>
        <div className="flex items-center gap-2">
          {isEditing && (
            <span className="text-xs text-blue-600 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full font-medium">
              Edited {charDiff > 0 ? `+${charDiff}` : charDiff} chars
            </span>
          )}
          <span className="text-xs text-gray-400">
            {text.length} chars
          </span>
        </div>
      </div>

      <p className="text-xs text-gray-500 mb-2">
        Review and edit before approving. This exact text will be sent to the customer.
      </p>

      <textarea
        className="w-full h-40 text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded-lg p-3 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:border-indigo-400 leading-relaxed"
        value={text}
        onChange={handleChange}
      />

      {isEditing && (
        <button
          className="mt-2 text-xs text-gray-500 hover:text-gray-700 underline"
          onClick={() => { setText(initialDraft); onChange(initialDraft); setIsEditing(false); }}
        >
          Reset to AI draft
        </button>
      )}
    </div>
  );
}
