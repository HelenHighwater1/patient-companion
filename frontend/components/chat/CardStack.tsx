"use client";

import { useEffect, useState } from "react";
import type { CardBody } from "@/lib/types";

const REVEAL_MS = 1500;

/** Staged card reveal — cards appear one at a time like messages arriving. */
export function CardStack({ cards, concerns }: { cards: CardBody[]; concerns: string[] }) {
  const total = cards.length + (concerns.length > 0 ? 1 : 0);
  const [visible, setVisible] = useState(0);

  useEffect(() => {
    if (visible >= total) return;
    const t = setTimeout(() => setVisible((v) => v + 1), visible === 0 ? 300 : REVEAL_MS);
    return () => clearTimeout(t);
  }, [visible, total]);

  return (
    <div className="space-y-3" aria-live="polite">
      {cards.slice(0, visible).map((card, i) => (
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

      {concerns.length > 0 && visible > cards.length && (
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

      {visible < total && (
        <div className="flex items-center gap-2 px-2 text-xs text-warm-700/60">
          <span className="dot-pulse h-1.5 w-1.5 rounded-full bg-brand-400" />
          <span className="dot-pulse h-1.5 w-1.5 rounded-full bg-brand-400" />
          <span className="dot-pulse h-1.5 w-1.5 rounded-full bg-brand-400" />
          <span className="ml-1">more coming…</span>
        </div>
      )}
    </div>
  );
}
