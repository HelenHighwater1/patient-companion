"use client";

import { forwardRef, useState } from "react";
import { citationsFor, sourceTypeInfo } from "@/lib/evidence";
import type { Citation, Source } from "@/lib/types";

function verdict(c: Citation) {
  const g = c.grounding;
  if (!g) return null;
  if (!g.checked) return { label: "Not checked", cls: "bg-terracotta-100 text-terracotta-800" };
  if (g.judge_score === 3) return { label: "Not verified", cls: "bg-terracotta-100 text-terracotta-800" };
  if (g.flagged) return { label: "Low overlap", cls: "bg-terracotta-100 text-terracotta-800" };
  if (g.judge_score === 2) return { label: "Partly supported", cls: "bg-ochre-100 text-ochre-800" };
  return { label: "Supported", cls: "bg-brand-100 text-brand-800" };
}

interface Props {
  source: Source;
  rank: number;
  citations: Citation[];
  highlighted: boolean;
  onHover: (hovering: boolean) => void;
}

export const SourceCard = forwardRef<HTMLDivElement, Props>(function SourceCard(
  { source, rank, citations, highlighted, onHover },
  ref,
) {
  const [expanded, setExpanded] = useState(false);
  const info = sourceTypeInfo(source.source_type);
  const claims = citationsFor(source, citations);
  const markers = source.markers ?? claims.map((c) => c.marker);
  const cosine = source.dense_cosine;
  const meta = [source.section_path || source.section, source.year].filter(Boolean).join(" · ");

  return (
    <div
      ref={ref}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
      className={`card-in rounded-2xl p-3 transition-all duration-500 ${
        highlighted
          ? "bg-ochre-50 shadow-float-lg ring-2 ring-ochre-400"
          : source.cited === false
            ? "bg-warm-50/60"
            : "bg-warm-50 hover:shadow-float"
      }`}
    >
      <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
        {markers.map((m) => (
          <span
            key={m}
            className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-ochre-100 px-1 text-[10px] font-extrabold text-ochre-900"
          >
            {m}
          </span>
        ))}
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${info.badge}`}>
          {info.label}
        </span>
        {source.cited === false && (
          <span className="rounded-full bg-warm-200 px-2 py-0.5 text-[10px] font-bold text-warm-700">
            retrieved, not cited
          </span>
        )}
        <span className="ml-auto text-[10px] font-bold text-warm-700/60">#{rank}</span>
      </div>

      {source.url ? (
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="block text-sm font-bold leading-snug text-warm-900 hover:text-brand-700 hover:underline"
        >
          {source.title ?? source.source}
        </a>
      ) : (
        <p className="text-sm font-bold leading-snug text-warm-900">{source.title ?? source.source}</p>
      )}
      {meta && <p className="mt-0.5 truncate text-[11px] text-warm-700/70" title={meta}>{meta}</p>}

      {source.excerpt && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 block w-full text-left"
          title={expanded ? "Show less" : "Show the full passage"}
        >
          <blockquote
            className={`border-l-2 border-ochre-200 pl-2.5 text-xs leading-relaxed text-warm-800 ${
              expanded ? "" : "line-clamp-4"
            }`}
          >
            {source.excerpt}
          </blockquote>
        </button>
      )}

      {claims.length > 0 && (
        <ul className="mt-2.5 space-y-1.5">
          {claims.map((c) => {
            const v = verdict(c);
            return (
              <li key={c.marker} className="rounded-xl bg-paper px-2.5 py-1.5 text-xs leading-snug">
                <span className="font-bold text-ochre-800">[{c.marker}]</span>{" "}
                <span className="text-warm-800">{c.claim}</span>
                {v && (
                  <span className={`ml-1.5 inline-block rounded-full px-1.5 py-px text-[10px] font-bold ${v.cls}`}>
                    {v.label}
                    {c.grounding?.cosine != null && ` · ${c.grounding.cosine.toFixed(2)}`}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {cosine != null && (
        <div className="mt-2.5 flex items-center gap-2" title="Embedding similarity to your question">
          <span className="text-[10px] font-bold text-warm-700/70">match</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-warm-200">
            <div
              className="h-full rounded-full bg-brand-500"
              style={{ width: `${Math.max(4, Math.min(100, cosine * 100))}%` }}
            />
          </div>
          <span className="text-[10px] tabular-nums text-warm-700/70">{cosine.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
});
