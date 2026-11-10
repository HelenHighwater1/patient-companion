"use client";

import { useRef, useState } from "react";

interface Props {
  disabled: boolean;
  onSend: (text: string) => void;
  onUpload: (file: File) => void;
}

export function ChatInput({ disabled, onSend, onUpload }: Props) {
  const [value, setValue] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    setValue("");
    onSend(text);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) onUpload(file);
      }}
      className={`rounded-2xl border bg-white p-3 shadow-sm transition-colors ${
        dragging ? "border-brand-400 ring-2 ring-brand-200" : "border-warm-200"
      }`}
    >
      <div className="flex items-end gap-2">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          title="Upload a document (PDF, EML, or TXT)"
          aria-label="Upload a document"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-warm-200 text-warm-700 transition-colors hover:bg-warm-100 disabled:opacity-40"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
            <path d="M12 5v14M5 12h14" strokeLinecap="round" />
          </svg>
        </button>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.eml,.email,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = "";
          }}
        />
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          disabled={disabled}
          rows={1}
          placeholder="Ask about your document, or about ALS care…"
          aria-label="Message"
          className="max-h-32 flex-1 resize-none rounded-lg px-3 py-2 text-sm text-warm-900 placeholder:text-warm-700/50 focus:outline-none focus:ring-2 focus:ring-brand-200 disabled:opacity-50"
        />
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="h-9 shrink-0 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-700 disabled:opacity-40"
        >
          Send
        </button>
      </div>
      <p className="mt-2 px-1 text-[11px] text-warm-700/60">
        Drop a document anywhere in this box to summarize it · fictional samples only —
        no real health info
      </p>
    </div>
  );
}
