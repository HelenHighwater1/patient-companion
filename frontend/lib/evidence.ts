import type { Citation, Source } from "./types";

export const sourceKey = (s: { source: string; chunk_index?: number }) =>
  `${s.source}:${s.chunk_index ?? 0}`;

export const SOURCE_TYPES: Record<string, { label: string; badge: string }> = {
  "patient-education": { label: "Patient education", badge: "bg-brand-100 text-brand-800" },
  "clinical-reference": { label: "Clinical reference", badge: "bg-plum-100 text-plum-700" },
  "research-article": { label: "Research article", badge: "bg-slate-100 text-slate-700" },
};

export const sourceTypeInfo = (t: string | null | undefined) =>
  SOURCE_TYPES[t ?? ""] ?? { label: "Source", badge: "bg-warm-200 text-warm-700" };

/** Citations that point at a given retrieved passage. */
export const citationsFor = (s: Source, citations: Citation[]) =>
  citations.filter(
    (c) =>
      c.source === s.source && (c.chunk_index === undefined || c.chunk_index === s.chunk_index),
  );

/** A citation counts as supported only if it was actually checked and nothing flagged it. */
export function isSupported(c: Citation): boolean {
  const g = c.grounding;
  return !!g && g.checked && !g.flagged && (g.judge_score ?? 1) < 3;
}
