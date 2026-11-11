"use client";

import { useEffect, useState } from "react";
import { documentUrl, fetchDocumentText } from "@/lib/api";
import type { SampleDocument } from "@/lib/types";

interface Props {
  doc: SampleDocument;
  onClose: () => void;
  onLoad: (doc: SampleDocument) => void;
}

export function PreviewModal({ doc, onClose, onLoad }: Props) {
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const isPdf = doc.file_type === "PDF";

  useEffect(() => {
    if (!isPdf) {
      fetchDocumentText(doc.filename)
        .then(setText)
        .catch(() => setError(true));
    }
  }, [doc.filename, isPdf]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-warm-900/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-4xl bg-paper shadow-float-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-warm-100 px-6 py-4">
          <h2 className="font-display text-base font-semibold text-warm-900">{doc.title}</h2>
          <button
            onClick={onClose}
            aria-label="Close preview"
            className="rounded-lg px-2 py-1 text-warm-700 hover:bg-warm-100"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-6">
          {isPdf ? (
            <iframe
              src={documentUrl(doc.filename)}
              title={doc.title}
              className="h-[60vh] w-full rounded-2xl border border-warm-200"
            />
          ) : error ? (
            <p className="text-sm text-warm-700">Couldn&apos;t load a preview.</p>
          ) : (
            <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-warm-700">
              {text ?? "Loading…"}
            </pre>
          )}
        </div>
        <div className="border-t border-warm-100 px-6 py-4">
          <button
            onClick={() => onLoad(doc)}
            className="w-full rounded-full bg-brand-600 px-4 py-2.5 font-medium text-white transition-colors hover:bg-brand-700"
          >
            Load this document into the chat
          </button>
        </div>
      </div>
    </div>
  );
}
