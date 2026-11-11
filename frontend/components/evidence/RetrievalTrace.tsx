"use client";

import { isSupported } from "@/lib/evidence";
import type { Citation, RetrievalTrace as Trace } from "@/lib/types";

function Step({
  tone,
  title,
  children,
}: {
  tone: "brand" | "ochre" | "plum" | "terracotta";
  title: string;
  children?: React.ReactNode;
}) {
  const dot = {
    brand: "bg-brand-500",
    ochre: "bg-ochre-500",
    plum: "bg-plum-500",
    terracotta: "bg-terracotta-500",
  }[tone];
  return (
    <li className="relative pb-3 pl-5 last:pb-0">
      <span className={`absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full ${dot}`} />
      <p className="text-xs font-bold text-warm-800">{title}</p>
      {children && <div className="mt-0.5 text-xs leading-snug text-warm-700">{children}</div>}
    </li>
  );
}

const fmt = (n: number) => n.toFixed(2);

export function RetrievalTrace({
  trace,
  citations,
  pending,
  failed = false,
}: {
  trace: Trace;
  citations: Citation[];
  pending: boolean;
  failed?: boolean;
}) {
  const { counts, gate } = trace;
  const outOfScope = trace.refusal_reason === "out_of_scope";
  const judged = citations.filter((c) => c.grounding);
  const supported = judged.filter(isSupported).length;
  const unchecked = judged.filter((c) => !c.grounding!.checked).length;
  const total = trace.latencies_ms.total_ms;

  return (
    <details open className="group rounded-2xl bg-warm-50 p-3">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2">
        <span className="font-display text-base font-bold text-warm-900">How this was found</span>
        <span className="text-[11px] text-warm-700/60">
          {total !== undefined ? `${Math.round(total)} ms · ` : ""}
          <span className="group-open:hidden">show</span>
          <span className="hidden group-open:inline">hide</span>
        </span>
      </summary>
      <ol className="mt-3 border-l border-warm-200 pl-0 [&>li]:-ml-[5px]">
        <Step
          tone="brand"
          title={
            outOfScope
              ? "Scope check: outside this knowledge base"
              : `Rewrote your question into ${trace.query_variants.length} ${trace.query_variants.length === 1 ? "search" : "searches"}`
          }
        >
          {outOfScope ? (
            "Nothing was searched, so no sources were spent on it."
          ) : (
            <ul className="mt-1 space-y-1">
              {trace.query_variants.map((q, i) => (
                <li key={i} className="rounded-lg bg-paper px-2 py-1 italic">
                  “{q}”
                </li>
              ))}
            </ul>
          )}
        </Step>
        {!outOfScope && (
          <>
            <Step tone="plum" title="Searched two ways">
              By meaning (embeddings): <strong>{counts.dense}</strong> passages · by keywords
              (BM25): <strong>{counts.bm25}</strong> passages
            </Step>
            <Step tone="ochre" title="Merged the rankings">
              Reciprocal rank fusion → <strong>{counts.fused}</strong> candidates, kept the top{" "}
              <strong>{counts.returned}</strong>
            </Step>
          </>
        )}
        {gate && (
          <Step
            tone={gate.passed ? "brand" : "terracotta"}
            title={gate.passed ? "Confidence check passed" : "Confidence check failed"}
          >
            {gate.method === "dense_cosine" ? "Best similarity" : "Rerank margin"}{" "}
            <strong>{fmt(gate.value)}</strong> {gate.value >= gate.threshold ? "≥" : "<"}{" "}
            threshold {fmt(gate.threshold)}
            {gate.passed && gate.value < gate.threshold && gate.top_score !== undefined && (
              <>
                , but the top passage scored <strong>{fmt(gate.top_score)}</strong> (≥ 0), which
                is confident enough on its own
              </>
            )}
            {!gate.passed &&
              (gate.top_score !== undefined
                ? `, and the top passage scored ${fmt(gate.top_score)} (< 0)`
                : "")}
            {!gate.passed && " — so it declined to answer rather than guess."}
          </Step>
        )}
        {!trace.refused && failed && (
          <Step tone="terracotta" title="Answer didn't finish">
            Something went wrong after retrieval, so these passages were never used.
          </Step>
        )}
        {!trace.refused && !failed && (
          <Step
            tone={pending ? "ochre" : judged.length && supported < judged.length ? "terracotta" : "brand"}
            title={pending ? "Drafting and fact-checking…" : "Fact-checked every claim"}
          >
            {pending
              ? "Each claim will be compared against the passage it cites."
              : judged.length
                ? `${supported} of ${judged.length} cited claims matched their source passage.` +
                  (unchecked
                    ? ` ${unchecked} cited a passage that wasn't retrieved, so ${unchecked === 1 ? "it" : "they"} couldn't be checked.`
                    : "")
                : "No individual claims to check."}
          </Step>
        )}
      </ol>
    </details>
  );
}
