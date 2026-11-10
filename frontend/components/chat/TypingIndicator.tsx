"use client";

import type { Stage } from "@/lib/types";

const STAGE_LABELS: Record<Stage, string> = {
  reading: "Reading your document…",
  searching: "Searching the knowledge base…",
  answering: "Drafting an answer from the sources…",
  checking: "Checking every claim against the sources…",
  rewriting: "Rewriting it for you…",
};

export function TypingIndicator({ stage }: { stage: Stage | null }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-sm ring-1 ring-warm-200">
      <span className="flex gap-1" aria-hidden>
        <span className="dot-pulse h-2 w-2 rounded-full bg-brand-400" />
        <span className="dot-pulse h-2 w-2 rounded-full bg-brand-400" />
        <span className="dot-pulse h-2 w-2 rounded-full bg-brand-400" />
      </span>
      <span className="text-sm text-warm-700">
        {stage ? STAGE_LABELS[stage] : "Thinking…"}
      </span>
    </div>
  );
}
