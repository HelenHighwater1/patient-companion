"use client";

import { useEffect, useRef, useState } from "react";
import type { Citation, Source } from "@/lib/types";

interface Props {
  text: string;
  questions: string[];
  citations: Citation[];
  sources: Source[];
  flaggedGaps: string[];
  disclaimer: string;
  onAskQuestion: (q: string) => void;
}

/** Render the response with [n] markers turned into citation badges. */
function WithCitations({
  text,
  citations,
  onCitationClick,
}: {
  text: string;
  citations: Citation[];
  onCitationClick: (marker: number) => void;
}) {
  const parts = text.split(/(\[\d+\])/g);
  const byMarker = new Map(citations.map((c) => [c.marker, c]));
  return (
    <p className="whitespace-pre-wrap text-sm leading-relaxed text-warm-800">
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (!m) return <span key={i}>{part}</span>;
        const marker = Number(m[1]);
        const cit = byMarker.get(marker);
        return (
          <button
            key={i}
            type="button"
            onClick={() => onCitationClick(marker)}
            title={cit ? `${cit.title ?? cit.source}\n${cit.claim}` : "source"}
            className="mx-0.5 inline-flex h-4 min-w-4 cursor-pointer items-center justify-center rounded-full bg-ochre-100 px-1 align-super text-[10px] font-bold text-ochre-900 transition-colors hover:bg-ochre-200"
          >
            {marker}
          </button>
        );
      })}
    </p>
  );
}

export function AnswerMessage({
  text,
  questions,
  citations,
  sources,
  flaggedGaps,
  disclaimer,
  onAskQuestion,
}: Props) {
  const [showSources, setShowSources] = useState(false);
  const [activeSource, setActiveSource] = useState<{ marker: number; tick: number } | null>(
    null,
  );
  const sourceRefs = useRef(new Map<number, HTMLDivElement>());
  const tick = useRef(0);

  const handleCitationClick = (marker: number) => {
    setShowSources(true);
    setActiveSource({ marker, tick: ++tick.current });
  };

  useEffect(() => {
    if (!activeSource || !showSources) return;
    sourceRefs.current
      .get(activeSource.marker)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
    const t = window.setTimeout(() => setActiveSource(null), 1600);
    return () => window.clearTimeout(t);
  }, [activeSource, showSources]);

  return (
    <div className="space-y-3 rounded-3xl rounded-bl-md bg-warm-50 p-4">
      <WithCitations text={text} citations={citations} onCitationClick={handleCitationClick} />

      {flaggedGaps.length > 0 && (
        <div className="rounded-2xl bg-terracotta-50 p-3">
          <p className="mb-1 text-xs font-bold text-terracotta-800">
            Worth confirming with your doctor:
          </p>
          <ul className="list-disc space-y-0.5 pl-4 text-xs text-terracotta-800">
            {flaggedGaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}

      {questions.length > 0 && (
        <div>
          <p className="mb-1.5 font-display text-sm font-semibold text-warm-800">
            For your next appointment
          </p>
          <div className="flex flex-col gap-1.5">
            {questions.map((q, i) => (
              <button
                key={i}
                onClick={() => onAskQuestion(q)}
                title="Ask this question now"
                className="float-hover rounded-2xl bg-paper px-3 py-2 shadow-float text-left text-xs leading-snug text-brand-900 hover:bg-brand-50"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between border-t border-warm-200/70 pt-2">
        <button
          onClick={() => {
            setActiveSource(null);
            setShowSources((v) => !v);
          }}
          className="text-xs font-bold text-brand-700 hover:underline"
        >
          {showSources ? "Hide sources" : `Sources (${citations.length || sources.length})`}
        </button>
      </div>

      {showSources && (
        <div className="space-y-2 rounded-2xl bg-paper p-3 text-xs">
          {(citations.length > 0 ? citations : sources).map((s, i) => {
            const key = "marker" in s ? s.marker : i + 1;
            return (
              <div
                key={i}
                ref={(el) => {
                  if (el) sourceRefs.current.set(key, el);
                  else sourceRefs.current.delete(key);
                }}
                className={`rounded px-1 leading-snug transition-colors duration-500 ${
                  activeSource?.marker === key ? "bg-ochre-100 ring-1 ring-ochre-200" : ""
                }`}
              >
                <span className="font-semibold text-brand-800">
                  {"marker" in s ? `[${s.marker}] ` : "• "}
                </span>
                {s.url ? (
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-brand-700 hover:underline"
                  >
                    {s.title ?? s.source}
                  </a>
                ) : (
                  <span className="font-medium text-warm-800">{s.title ?? s.source}</span>
                )}
                {"claim" in s && s.claim && (
                  <span className="block pl-5 text-warm-700/80">{s.claim}</span>
                )}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-[11px] italic leading-snug text-warm-700/60">{disclaimer}</p>
    </div>
  );
}
