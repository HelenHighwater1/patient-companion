"use client";

export function Header({
  onOpenTour,
  onOpenEvidence,
}: {
  onOpenTour: () => void;
  onOpenEvidence: () => void;
}) {
  return (
    <header className="relative z-30 px-4 pt-4">
      <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-2 rounded-3xl bg-paper px-5 py-3 shadow-float">
        <div className="flex items-center gap-3">
          <div
            aria-hidden
            className="flex h-10 w-10 items-center justify-center rounded-2xl bg-terracotta-500 text-white"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
              <path d="M12 21s-7-4.5-9.5-9C.5 8 2.5 4 6.5 4c2.2 0 3.9 1.3 5.5 3.4C13.6 5.3 15.3 4 17.5 4c4 0 6 4 4 8-2.5 4.5-9.5 9-9.5 9z" />
            </svg>
          </div>
          <div>
            <p className="font-display text-base font-bold uppercase leading-tight tracking-[0.12em] text-warm-900 sm:text-xl sm:tracking-[0.16em]">
              Patient Companion
            </p>
            <p className="hidden text-xs text-warm-700/70 sm:block">medical documents, translated kindly</p>
          </div>
        </div>
        <div className="flex items-center gap-1 sm:gap-3">
          <span className="hidden rounded-full bg-plum-50 px-3 py-1 text-xs font-bold text-plum-700 sm:inline">
            ALS knowledge base · demo
          </span>
          <button
            onClick={onOpenEvidence}
            className="rounded-full bg-ochre-100 px-3 py-2 text-sm font-bold text-ochre-900 transition-colors hover:bg-ochre-200 xl:hidden"
          >
            Evidence
          </button>
          <button
            onClick={onOpenTour}
            className="rounded-full px-3 py-2 text-sm font-bold text-warm-700 transition-colors hover:bg-warm-100"
          >
            Tour
          </button>
        </div>
      </div>
    </header>
  );
}
