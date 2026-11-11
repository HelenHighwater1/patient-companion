"use client";

import type { PrepSheet } from "@/lib/types";

interface Props {
  sheet: PrepSheet;
  documentName: string | null;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <h3 className="mb-2 border-b border-warm-200 pb-1 text-sm font-semibold uppercase tracking-wide text-brand-800">
        {title}
      </h3>
      {children}
    </section>
  );
}

export function PrepSheetModal({ sheet, documentName, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-warm-900/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="flex max-h-[88vh] w-full max-w-2xl flex-col rounded-4xl bg-paper shadow-float-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-warm-100 px-6 py-4 print:hidden">
          <h2 className="font-display text-xl font-bold text-warm-900">Appointment prep sheet</h2>
          <div className="flex gap-2">
            <button
              onClick={() => window.print()}
              className="rounded-full bg-brand-600 px-4 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
            >
              Print / save as PDF
            </button>
            <button
              onClick={onClose}
              aria-label="Close"
              className="rounded-lg px-2 py-1 text-warm-700 hover:bg-warm-100"
            >
              ✕
            </button>
          </div>
        </div>

        <div id="prep-sheet-print" className="flex-1 overflow-y-auto px-6 py-5">
          <header className="mb-6">
            <h1 className="font-display text-2xl font-bold text-warm-900">Preparing for my appointment</h1>
            <p className="text-xs text-warm-700/70">
              {documentName ? `About: ${documentName} · ` : ""}Made with the Patient Companion demo —
              not medical advice.
            </p>
          </header>

          {sheet.document_summary && (
            <Section title="In plain language">
              <p className="text-sm leading-relaxed text-warm-800">{sheet.document_summary}</p>
            </Section>
          )}

          {sheet.your_questions.length > 0 && (
            <Section title="My questions">
              <ul className="space-y-2">
                {sheet.your_questions.map((q, i) => (
                  <li key={i} className="flex gap-2 text-sm text-warm-800">
                    <span className="mt-0.5 h-4 w-4 shrink-0 rounded border border-warm-300" />
                    {q}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {sheet.suggested_questions.length > 0 && (
            <Section title="Also worth asking">
              <ul className="space-y-2">
                {sheet.suggested_questions.map((q, i) => (
                  <li key={i} className="flex gap-2 text-sm text-warm-800">
                    <span className="mt-0.5 h-4 w-4 shrink-0 rounded border border-warm-300" />
                    {q}
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {sheet.topics_to_raise.length > 0 && (
            <Section title="Topics to raise">
              <ul className="list-disc space-y-1 pl-5 text-sm text-warm-800">
                {sheet.topics_to_raise.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </Section>
          )}

          {sheet.key_terms.length > 0 && (
            <Section title="Words worth knowing">
              <dl className="space-y-1.5">
                {sheet.key_terms.map((kt, i) => (
                  <div key={i} className="text-sm">
                    <dt className="inline font-medium text-warm-900">{kt.term}</dt>
                    <dd className="inline text-warm-700"> — {kt.definition}</dd>
                  </div>
                ))}
              </dl>
            </Section>
          )}
        </div>
      </div>
    </div>
  );
}
