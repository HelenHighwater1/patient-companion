"use client";

export function AboutModal({ onClose }: { onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-warm-900/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="max-h-[80vh] w-full max-w-xl overflow-y-auto rounded-4xl bg-paper p-8 shadow-float-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-3 font-display text-3xl font-bold text-warm-900">About this demo</h2>
        <div className="space-y-3 text-sm leading-relaxed text-warm-700">
          <p>
            Patient Companion translates dense medical documents into staged,
            plain-language cards, then lets you ask questions answered only from a vetted
            knowledge base — currently ALS (NINDS, NCBI GeneReviews, and PubMed Central
            research articles).
          </p>
          <p>
            Every answer passes through a pipeline: the question is checked for scope and
            rewritten for retrieval, matched against the knowledge base, drafted with
            citations, audited claim-by-claim against the cited sources, then rewritten
            for warmth and clarity at your chosen reading level.
          </p>
          <p className="rounded-2xl bg-ochre-50 p-4 text-ochre-900">
            <strong>Honest limits:</strong> this is a technical demo — not HIPAA
            compliant, not clinically validated, and not a substitute for medical advice.
            Never enter real patient information.
          </p>
        </div>
        <button
          onClick={onClose}
          className="mt-6 w-full rounded-full bg-brand-600 px-4 py-3 font-medium text-white transition-colors hover:bg-brand-700"
        >
          Close
        </button>
      </div>
    </div>
  );
}
