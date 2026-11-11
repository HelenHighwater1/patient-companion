"use client";

import { useEffect, useRef } from "react";
import { sourceKey } from "@/lib/evidence";
import type { CorpusSummary, Evidence } from "@/lib/types";
import { CorpusOverview } from "./CorpusOverview";
import { RetrievalTrace } from "./RetrievalTrace";
import { SourceCard } from "./SourceCard";

export interface EvidenceFocus {
  marker: number;
  tick: number;
}

interface Props {
  corpus: CorpusSummary | null;
  evidence: Evidence | null;
  focus: EvidenceFocus | null;
  hoveredKey: string | null;
  onHoverSource: (key: string | null) => void;
  onClear: () => void;
  onClose?: () => void;
}

export function EvidencePanel({
  corpus,
  evidence,
  focus,
  hoveredKey,
  onHoverSource,
  onClear,
  onClose,
}: Props) {
  const cardRefs = useRef(new Map<string, HTMLDivElement>());

  const sources = evidence?.sources ?? [];
  const ranked = sources.map((s, i) => ({ s, rank: i + 1 }));
  const cited = ranked
    .filter(({ s }) => s.cited)
    .sort((a, b) => Math.min(...(a.s.markers ?? [0])) - Math.min(...(b.s.markers ?? [0])));
  const rest = ranked.filter(({ s }) => !s.cited);
  const focusedKey =
    focus && evidence
      ? (() => {
          const s = sources.find((x) => x.markers?.includes(focus.marker));
          return s ? sourceKey(s) : null;
        })()
      : null;

  useEffect(() => {
    if (focusedKey) {
      cardRefs.current.get(focusedKey)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [focusedKey, focus?.tick]);

  const card = ({ s, rank }: (typeof ranked)[number]) => {
    const key = sourceKey(s);
    return (
      <SourceCard
        key={key}
        ref={(el) => {
          if (el) cardRefs.current.set(key, el);
          else cardRefs.current.delete(key);
        }}
        source={s}
        rank={rank}
        citations={evidence?.citations ?? []}
        highlighted={key === focusedKey || key === hoveredKey}
        onHover={(h) => onHoverSource(h ? key : null)}
      />
    );
  };

  return (
    <aside className="flex h-full flex-col rounded-3xl bg-paper shadow-float">
      <div className="flex items-start justify-between gap-2 border-b border-warm-100 px-4 py-3">
        <div className="min-w-0">
          <h2 className="font-display text-lg font-semibold text-warm-900">
            {evidence ? "Evidence" : "Knowledge base"}
          </h2>
          <p className="truncate text-xs text-warm-700/70" title={evidence?.question}>
            {evidence ? `For: “${evidence.question}”` : "What answers are allowed to draw on"}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {evidence && (
            <button
              onClick={onClear}
              className="rounded-full px-2.5 py-1 text-[11px] font-bold text-brand-700 hover:bg-brand-50"
            >
              Corpus
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close evidence"
              className="rounded-full px-2 py-1 text-warm-700 hover:bg-warm-100"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4" aria-live="polite">
        {!evidence && <CorpusOverview corpus={corpus} />}

        {evidence?.trace && (
          <RetrievalTrace
            trace={evidence.trace}
            citations={evidence.citations}
            pending={evidence.status === "answering"}
          />
        )}

        {evidence?.status === "refused" && sources.length === 0 && (
          <p className="rounded-2xl bg-terracotta-50 p-3 text-xs leading-relaxed text-terracotta-800">
            No passages were confident enough to answer from, so the companion said so instead
            of guessing.
          </p>
        )}

        {evidence?.status === "answering" && sources.length > 0 && (
          <>
            <h3 className="px-1 text-xs font-bold text-warm-700/80">
              Retrieved passages · drafting answer…
            </h3>
            {ranked.map(card)}
          </>
        )}

        {evidence?.status !== "answering" && cited.length > 0 && (
          <>
            <h3 className="px-1 text-xs font-bold text-warm-700/80">Cited in the answer</h3>
            {cited.map(card)}
          </>
        )}
        {evidence?.status !== "answering" && rest.length > 0 && (
          <>
            <h3 className="px-1 pt-1 text-xs font-bold text-warm-700/80">
              {cited.length ? "Also retrieved" : "Retrieved passages"}
            </h3>
            {rest.map(card)}
          </>
        )}
      </div>
    </aside>
  );
}
