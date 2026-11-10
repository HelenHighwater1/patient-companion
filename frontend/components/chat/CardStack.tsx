"use client";

import { useEffect, useState } from "react";
import type { CardBody } from "@/lib/types";

interface Props {
  cards: CardBody[];
  concerns: string[];
  /** True while the stream may still deliver more sections. */
  pending: boolean;
}

/** Click-to-advance card reveal — the patient paces the recap themselves. */
export function CardStack({ cards, concerns, pending }: Props) {
  const total = cards.length + (concerns.length > 0 ? 1 : 0);
  const [visible, setVisible] = useState(1);
  const [waiting, setWaiting] = useState(false);
  const shown = Math.min(visible, total);
  const ready = shown < total;

  // The user clicked ahead before the next section arrived — reveal it as
  // soon as the stream delivers it.
  useEffect(() => {
    if (!waiting) return;
    if (ready) {
      setVisible((v) => v + 1);
      setWaiting(false);
    } else if (!pending) {
      setWaiting(false);
    }
  }, [waiting, ready, pending]);

  // Nothing arrived yet — the "Reading your document…" indicator covers it.
  if (total === 0) return null;

  return (
    <div className="space-y-3" aria-live="polite">
      {cards.slice(0, shown).map((card, i) => (
        <div
          key={card.key}
          className="card-in overflow-hidden rounded-2xl rounded-bl-sm bg-white shadow-sm ring-1 ring-warm-200"
        >
          <div className="border-b border-warm-100 bg-brand-50/60 px-4 py-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-brand-800">
              {i + 1} · {card.label}
            </span>
          </div>
          <div className="px-4 py-3 text-sm leading-relaxed text-warm-800">
            {Array.isArray(card.body) ? (
              <ol className="list-decimal space-y-2 pl-5">
                {card.body.map((q, j) => (
                  <li key={j}>{q}</li>
                ))}
              </ol>
            ) : (
              card.body.split("•").map((part, j) => (
                <p key={j} className={j > 0 ? "mt-2" : ""}>
                  {part.trim()}
                </p>
              ))
            )}
          </div>
        </div>
      ))}

      {concerns.length > 0 && shown > cards.length && (
        <div className="card-in rounded-2xl rounded-bl-sm bg-amber-50 px-4 py-3 shadow-sm ring-1 ring-amber-200">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-800">
            Things this document might have you thinking about
          </p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-warm-800">
            {concerns.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-amber-800/80">
            These get saved into your appointment prep sheet.
          </p>
        </div>
      )}

      {waiting ? (
        <div className="flex items-center gap-2 px-2 text-xs text-warm-700/60">
          <span className="dot-pulse h-1.5 w-1.5 rounded-full bg-brand-400" />
          <span className="dot-pulse h-1.5 w-1.5 rounded-full bg-brand-400" />
          <span className="dot-pulse h-1.5 w-1.5 rounded-full bg-brand-400" />
          <span className="ml-1">Preparing the next section…</span>
        </div>
      ) : (
        (ready || pending) && (
          <button
            onClick={() => (ready ? setVisible(shown + 1) : setWaiting(true))}
            className="rounded-full border border-brand-200 bg-white px-4 py-1.5 text-xs font-medium text-brand-800 shadow-sm transition-colors hover:bg-brand-50"
          >
            Next section →
          </button>
        )
      )}
    </div>
  );
}
