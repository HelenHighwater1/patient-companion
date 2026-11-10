"use client";

export function Header({ onOpenAbout }: { onOpenAbout: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-warm-200 bg-white/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-3">
          <div
            aria-hidden
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
              <path d="M12 21s-7-4.5-9.5-9C.5 8 2.5 4 6.5 4c2.2 0 3.9 1.3 5.5 3.4C13.6 5.3 15.3 4 17.5 4c4 0 6 4 4 8-2.5 4.5-9.5 9-9.5 9z" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-semibold leading-tight text-warm-900">Patient Companion</p>
            <p className="text-xs text-warm-700/70">medical documents, translated kindly</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="hidden rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-800 sm:inline">
            ALS knowledge base · demo
          </span>
          <button
            onClick={onOpenAbout}
            className="rounded-lg px-3 py-2 text-sm font-medium text-warm-700 transition-colors hover:bg-warm-100"
          >
            About
          </button>
        </div>
      </div>
    </header>
  );
}
