"use client";

import type { Stage } from "@/lib/types";

const STAGE_LABELS: Record<Stage, string> = {
  reading: "Reading your document…",
  searching: "Searching the knowledge base…",
  answering: "Drafting an answer from the sources…",
  checking: "Checking every claim against the sources…",
};

export function TypingIndicator({ stage }: { stage: Stage | null }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl rounded-bl-sm bg-warm-50 px-4 py-3">
      <span className="flex gap-1" aria-hidden>
        <span className="dot-pulse h-2 w-2 rounded-full bg-ochre-400" />
        <span className="dot-pulse h-2 w-2 rounded-full bg-ochre-400" />
        <span className="dot-pulse h-2 w-2 rounded-full bg-ochre-400" />
      </span>
      <span className="text-sm text-warm-700">
        {stage ? STAGE_LABELS[stage] : "Thinking…"}
      </span>
    </div>
  );
}
