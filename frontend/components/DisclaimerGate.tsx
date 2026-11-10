"use client";

export function DisclaimerGate({ onAcknowledge }: { onAcknowledge: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-warm-900/60 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="disclaimer-title"
    >
      <div className="w-full max-w-lg rounded-2xl bg-white p-8 shadow-2xl">
        <div className="mb-4 inline-flex rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold text-brand-800">
          Demo project — please read
        </div>
        <h2 id="disclaimer-title" className="mb-3 text-xl font-semibold text-warm-900">
          This is a demonstration, not a medical tool.
        </h2>
        <ul className="mb-6 list-disc space-y-2 pl-5 text-sm leading-relaxed text-warm-700">
          <li>
            <strong>Do not enter real personal health information.</strong> This app sends
            whatever you type to third-party AI APIs. It is not HIPAA compliant and has no
            access controls.
          </li>
          <li>
            <strong>It is not medical advice.</strong> Answers come from a small demo
            knowledge base and a language model — your care team is always the authority.
          </li>
          <li>
            All included sample documents are <strong>entirely fictional</strong>.
          </li>
          <li>
            If you are in distress or crisis, please reach out to your care team or someone
            you trust.
          </li>
        </ul>
        <button
          onClick={onAcknowledge}
          autoFocus
          className="w-full rounded-xl bg-brand-600 px-4 py-3 font-medium text-white transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2"
        >
          I understand — show me the demo
        </button>
      </div>
    </div>
  );
}
