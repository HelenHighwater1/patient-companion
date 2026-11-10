"use client";

import type { SampleDocument } from "@/lib/types";

interface Props {
  documents: SampleDocument[];
  activeFilename: string | null;
  onLoad: (doc: SampleDocument) => void;
  onPreview: (doc: SampleDocument) => void;
}

const BADGE: Record<string, string> = {
  PDF: "bg-rose-50 text-rose-700",
  EMAIL: "bg-sky-50 text-sky-700",
};

export function DocumentPanel({ documents, activeFilename, onLoad, onPreview }: Props) {
  return (
    <aside className="flex h-full flex-col">
      <h2 className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-warm-700/70">
        Sample documents
      </h2>
      <p className="mb-3 px-1 text-xs text-warm-700/60">Fictional — safe to explore.</p>
      <div className="space-y-2 overflow-y-auto pr-1">
        {documents.map((doc) => (
          <div
            key={doc.filename}
            className={`rounded-xl border p-3 transition-colors ${
              doc.filename === activeFilename
                ? "border-brand-300 bg-brand-50"
                : "border-warm-200 bg-white hover:border-brand-200"
            }`}
          >
            <div className="mb-2 flex items-center justify-between gap-2">
              <span
                className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${
                  BADGE[doc.file_type] ?? "bg-warm-100 text-warm-700"
                }`}
              >
                {doc.file_type}
              </span>
            </div>
            <p className="mb-3 text-sm font-medium leading-snug text-warm-900">{doc.title}</p>
            <div className="flex gap-2">
              <button
                onClick={() => onLoad(doc)}
                className="flex-1 rounded-lg bg-brand-600 px-2 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand-700"
              >
                Load into chat
              </button>
              <button
                onClick={() => onPreview(doc)}
                className="rounded-lg border border-warm-200 px-2 py-1.5 text-xs font-medium text-warm-700 transition-colors hover:bg-warm-100"
              >
                Preview
              </button>
            </div>
          </div>
        ))}
        {documents.length === 0 && (
          <p className="rounded-xl border border-dashed border-warm-300 p-4 text-xs text-warm-700/70">
            No sample documents found. Is the API running?
          </p>
        )}
      </div>
    </aside>
  );
}
