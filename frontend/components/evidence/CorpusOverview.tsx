"use client";

import { useState } from "react";
import { SOURCE_TYPES, sourceTypeInfo } from "@/lib/evidence";
import type { CorpusSource, CorpusSummary } from "@/lib/types";

const PREVIEW_COUNT = 4;

function SourceGroup({ type, sources }: { type: string; sources: CorpusSource[] }) {
  const [expanded, setExpanded] = useState(false);
  const info = sourceTypeInfo(type);
  const chunks = sources.reduce((n, s) => n + s.chunks, 0);
  const shown = expanded ? sources : sources.slice(0, PREVIEW_COUNT);
  return (
    <div className="rounded-2xl bg-warm-50 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${info.badge}`}>
          {info.label}
        </span>
        <span className="text-[11px] text-warm-700/70">
          {sources.length} {sources.length === 1 ? "source" : "sources"} · {chunks} passages
        </span>
      </div>
      <ul className="space-y-1.5">
        {shown.map((s) => (
          <li key={s.source} className="flex items-baseline justify-between gap-2 text-xs">
            {s.url ? (
              <a
                href={s.url}
                target="_blank"
                rel="noreferrer"
                className="truncate font-semibold text-warm-800 hover:text-brand-700 hover:underline"
                title={s.title}
              >
                {s.title}
              </a>
            ) : (
              <span className="truncate font-semibold text-warm-800" title={s.title}>
                {s.title}
              </span>
            )}
            <span className="shrink-0 tabular-nums text-warm-700/60">{s.chunks}</span>
          </li>
        ))}
      </ul>
      {sources.length > PREVIEW_COUNT && (
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-[11px] font-bold text-brand-700 hover:underline"
        >
          {expanded ? "Show fewer" : `Show all ${sources.length}`}
        </button>
      )}
    </div>
  );
}

export function CorpusOverview({ corpus }: { corpus: CorpusSummary | null }) {
  if (!corpus) {
    return (
      <p className="rounded-2xl border border-dashed border-warm-300 p-4 text-xs text-warm-700/70">
        Couldn&apos;t load the knowledge base summary. Is the API running?
      </p>
    );
  }
  const order = [...Object.keys(SOURCE_TYPES), ""];
  const groups = new Map<string, CorpusSource[]>();
  for (const s of corpus.sources) {
    const t = s.source_type && SOURCE_TYPES[s.source_type] ? s.source_type : "";
    groups.set(t, [...(groups.get(t) ?? []), s]);
  }
  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed text-warm-700">
        Answers come only from this knowledge base. Ask a question and the passages it
        retrieves will show up here, with how each one was found and checked.
      </p>
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-2xl bg-brand-50 p-3">
          <p className="font-display text-2xl font-semibold text-brand-800">
            {corpus.chunk_count.toLocaleString()}
          </p>
          <p className="text-[11px] font-bold text-brand-800/70">searchable passages</p>
        </div>
        <div className="rounded-2xl bg-ochre-50 p-3">
          <p className="font-display text-2xl font-semibold text-ochre-800">
            {corpus.sources.length}
          </p>
          <p className="text-[11px] font-bold text-ochre-800/70">vetted sources</p>
        </div>
      </div>
      <div className="space-y-2">
        {order
          .filter((t) => groups.has(t))
          .map((t) => (
            <SourceGroup key={t || "other"} type={t} sources={groups.get(t)!} />
          ))}
      </div>
      <p className="text-[11px] leading-snug text-warm-700/60">
        {corpus.label}
        {corpus.embedding_model ? ` · embedded with ${corpus.embedding_model}` : ""}
        {corpus.built_at ? ` · built ${new Date(corpus.built_at).toLocaleDateString()}` : ""}
      </p>
    </div>
  );
}
