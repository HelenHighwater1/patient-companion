"use client";

import type { ReadingLevel } from "@/lib/types";

const OPTIONS: { value: ReadingLevel; label: string; hint: string }[] = [
  { value: "gentle", label: "Simpler", hint: "shortest sentences, easiest words" },
  { value: "standard", label: "Standard", hint: "plain everyday English" },
  { value: "detailed", label: "More detail", hint: "fuller explanations" },
];

export function ReadingLevelToggle({
  value,
  onChange,
}: {
  value: ReadingLevel;
  onChange: (v: ReadingLevel) => void;
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Reading level"
      className="inline-flex rounded-lg border border-warm-200 bg-warm-100 p-0.5"
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          role="radio"
          aria-checked={value === opt.value}
          title={opt.hint}
          onClick={() => onChange(opt.value)}
          className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
            value === opt.value
              ? "bg-white text-brand-800 shadow-sm"
              : "text-warm-700/80 hover:text-warm-900"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
