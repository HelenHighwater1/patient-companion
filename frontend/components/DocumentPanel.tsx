"use client";

import type { SampleDocument } from "@/lib/types";

interface Props {
  documents: SampleDocument[];
  status: "loading" | "ready" | "error";
  activeFilename: string | null;
  onLoad: (doc: SampleDocument) => void;
  onPreview: (doc: SampleDocument) => void;
}

const BADGE: Record<string, string> = {
  PDF: "bg-rose-100 text-rose-700",
  EMAIL: "bg-slate-100 text-slate-700",
};

export function DocumentPanel({ documents, status, activeFilename, onLoad, onPreview }: Props) {
  return (
    <aside className="flex h-full flex-col rounded-3xl bg-paper p-4 shadow-float">
      <h2 className="px-1 font-display text-xl font-bold text-warm-900">Sample documents</h2>
      <p className="mb-3 px-1 text-xs text-warm-700/70">Fictional — safe to explore.</p>
      <div className="-mx-1 space-y-3 overflow-y-auto px-1 pb-1">
        {documents.map((doc) => (
          <div
            key={doc.filename}
            className={`rounded-2xl p-3 transition-colors ${
              doc.filename === activeFilename
                ? "bg-brand-50 ring-2 ring-brand-300"
                : "bg-warm-50 hover:bg-warm-100"
            }`}
          >
            <span
              className={`mb-2 inline-block rounded-full px-2 py-0.5 text-[10px] font-extrabold tracking-wide ${
                BADGE[doc.file_type] ?? "bg-warm-200 text-warm-700"
              }`}
            >
              {doc.file_type}
            </span>
            <p className="mb-3 text-sm font-semibold leading-snug text-warm-900">{doc.title}</p>
            <div className="flex gap-2">
              <button
                onClick={() => onLoad(doc)}
                className="flex-1 rounded-full bg-brand-600 px-2 py-1.5 text-xs font-bold text-white transition-colors hover:bg-brand-700"
              >
                Load into chat
              </button>
              <button
                onClick={() => onPreview(doc)}
                className="rounded-full bg-paper px-3 py-1.5 text-xs font-bold text-warm-700 shadow-float transition-colors hover:bg-warm-100"
              >
                Preview
              </button>
            </div>
          </div>
        ))}
        {documents.length === 0 && (
          <div className="rounded-2xl border border-dashed border-warm-300 p-4 text-xs text-warm-700/70">
            {status === "loading" && (
              <div className="flex items-start gap-2.5">
                <span
                  aria-hidden
                  className="mt-0.5 h-3.5 w-3.5 shrink-0 animate-spin rounded-full border-2 border-warm-300 border-t-brand-600"
                />
                <div>
                  <p className="font-bold text-warm-800">Waking up the demo API…</p>
                  <p className="mt-1 leading-relaxed">
                    The backend runs on a free tier and can take up to a minute to boot after
                    inactivity. Documents will appear automatically.
                  </p>
                </div>
              </div>
            )}
            {status === "error" && (
              <p className="leading-relaxed">
                The demo API is still starting up after inactivity. Refresh the page in a few
                seconds and the sample documents will appear.
              </p>
            )}
            {status === "ready" && <p>No sample documents found.</p>}
          </div>
        )}
      </div>
    </aside>
  );
}
