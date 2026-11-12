"use client";

import { useCallback, useEffect, useState } from "react";

interface TourStep {
  /** data-tour attribute value of the section to spotlight, if any. */
  target?: string;
  title: string;
  body: React.ReactNode;
}

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const STEPS: TourStep[] = [
  {
    title: "Welcome to Patient Companion",
    body: (
      <>
        <p>
          This is a demo app, built to show how software could help patients
          with rare diseases understand what they&rsquo;re going through during
          the hardest days of their lives. Give it a medical document, like a
          specialist email or a test result, and it breaks it down into the
          parts that matter: what the document is, the main finding, what the
          tests showed, what happens next, and questions to bring to your
          doctor. Each part is revealed one at a time, so someone can take it
          in at their own pace, with kindness, while staying technically
          accurate.
        </p>
        <p>
          I built it because I wanted to practice implementing{" "}
          <strong>RAG (retrieval-augmented generation)</strong>, and there&rsquo;s
          no harder test for accuracy than a situation like this. The demo uses a
          knowledge base focused on ALS and comes with sample documents already
          prepared, so you can see the whole flow without uploading anything
          real.
        </p>
      </>
    ),
  },
  {
    target: "documents",
    title: "Fictional sample documents",
    body: (
      <p>
        Every document in this panel is invented, so it&rsquo;s safe to click
        around. <strong>Load into chat</strong> sends it through the intake
        pipeline; <strong>Preview</strong> shows the raw file. On small screens
        this panel is hidden.
      </p>
    ),
  },
  {
    target: "chat",
    title: "Staged cards & grounded answers",
    body: (
      <>
        <p>
          Once a user uploads one of the sample documents to the chat, it goes
          through an intake API call that walks the document section by section
          and returns five staged cards: what it is, the main finding, what the
          tests showed, what happens next, and questions worth asking your
          doctor. The prompts behind that call are tuned to keep everything
          technically correct while still sounding gentle.
        </p>
        <p>
          After that, you can ask questions of your own. Every answer is drawn
          only from the ALS corpus, with citations so you can see exactly where
          it came from.
        </p>
      </>
    ),
  },
  {
    target: "chat-toolbar",
    title: "Reading level & prep sheet",
    body: (
      <p>
        Switch the reading level of answers, or build a printable prep sheet to
        bring to your appointment: your questions, suggested topics, and a
        jargon glossary all in one place.
      </p>
    ),
  },
  {
    target: "evidence",
    title: "The evidence panel",
    body: (
      <p>
        Ever wonder where an answer actually came from? This panel is the
        receipt: it lists the corpus the app can draw on, the exact passages it
        pulled for your question, and which source each little citation number
        points to. On smaller screens you can open it from the{" "}
        <strong>Evidence</strong> button in the header.
      </p>
    ),
  },
  {
    title: "Just a demo",
    body: (
      <>
        <p>
          Worth saying plainly: this is a demo, not a real medical product, and
          it is <strong>not HIPAA compliant</strong>. Please don&rsquo;t enter
          real personal health information; whatever you type goes to
          third-party AI APIs.
        </p>
        <p>
          Answers come from a small demo knowledge base and a language model,
          so they are not medical advice. Your care team is always the
          authority. Every sample document here is fictional.
        </p>
      </>
    ),
  },
];

function measure(step: TourStep): Rect | null {
  if (!step.target) return null;
  const el = document.querySelector(`[data-tour="${step.target}"]`);
  const r = el?.getBoundingClientRect();
  if (!r || r.width <= 0 || r.height <= 0) return null;
  return { top: r.top, left: r.left, width: r.width, height: r.height };
}

/** Breathing room between the section and the spotlight edge/ring. */
const PAD = 8;
/** Corner radius of the spotlight hole and ring: card radius (24px) + PAD. */
const RADIUS = 32;

/** Mask style that cuts a rounded-rect hole (padded by PAD) out of a full-screen overlay. */
function holeMask(r: Rect): React.CSSProperties {
  const t = r.top - PAD, l = r.left - PAD;
  const w = r.width + PAD * 2, h = r.height + PAD * 2;
  const svg = encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}"><rect width="${w}" height="${h}" rx="${RADIUS}" fill="black"/></svg>`,
  );
  const holeImg = `url("data:image/svg+xml,${svg}")`;
  return {
    WebkitMaskImage: `linear-gradient(black, black), ${holeImg}`,
    maskImage: `linear-gradient(black, black), ${holeImg}`,
    WebkitMaskSize: `cover, ${w}px ${h}px`,
    maskSize: `cover, ${w}px ${h}px`,
    WebkitMaskPosition: `0 0, ${l}px ${t}px`,
    maskPosition: `0 0, ${l}px ${t}px`,
    WebkitMaskRepeat: `no-repeat, no-repeat`,
    maskRepeat: `no-repeat, no-repeat`,
    WebkitMaskComposite: "source-over, destination-out",
    maskComposite: "exclude",
  };
}

export function SiteTour({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const current = STEPS[step];
  const isFirst = step === 0;
  const isLast = step === STEPS.length - 1;

  useEffect(() => {
    const update = () => setRect(measure(current));
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [current]);

  const close = useCallback(() => onClose(), [onClose]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight" && !isLast) setStep((s) => s + 1);
      if (e.key === "ArrowLeft" && !isFirst) setStep((s) => s - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close, isFirst, isLast]);

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-labelledby="tour-title">
      {rect ? (
        <>
          <div
            aria-hidden
            className="fixed inset-0 bg-warm-900/60 backdrop-blur-sm transition-all duration-300"
            style={holeMask(rect)}
          />
          <div
            aria-hidden
            className="pointer-events-none fixed ring-[3px] ring-terracotta-500 transition-all duration-300"
            style={{
              top: rect.top - PAD,
              left: rect.left - PAD,
              width: rect.width + PAD * 2,
              height: rect.height + PAD * 2,
              borderRadius: RADIUS,
            }}
          />
        </>
      ) : (
        <div aria-hidden className="fixed inset-0 bg-warm-900/60 backdrop-blur-sm" />
      )}

      <div className="fixed left-1/2 top-1/2 flex h-[min(32rem,90vh)] w-[min(32rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-4xl bg-paper p-6 shadow-float-lg">
        <div className="mb-3 flex items-center justify-between">
          <span className="rounded-full bg-ochre-100 px-3 py-1 text-xs font-bold text-ochre-900">
            Demo tour · {step + 1} of {STEPS.length}
          </span>
          {!isLast && (
            <button
              onClick={close}
              className="text-xs font-bold text-warm-700/70 transition-colors hover:text-warm-900"
            >
              Skip tour
            </button>
          )}
        </div>

        <h2 id="tour-title" className="mb-3 font-display text-2xl font-bold text-warm-900">
          {current.title}
        </h2>
        <div className="flex-1 space-y-3 overflow-y-auto text-sm leading-relaxed text-warm-700">
          {current.body}
        </div>

        <div className="mt-6 flex items-center justify-between gap-3">
          <div aria-hidden className="flex gap-1.5">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className={`h-1.5 w-1.5 rounded-full ${i === step ? "bg-terracotta-500" : "bg-warm-200"}`}
              />
            ))}
          </div>
          <div className="flex gap-2">
            {!isFirst && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="rounded-full bg-paper px-4 py-2 text-sm font-bold text-warm-700 shadow-float transition-colors hover:bg-warm-100"
              >
                Back
              </button>
            )}
            <button
              onClick={() => (isLast ? close() : setStep((s) => s + 1))}
              autoFocus
              className="rounded-full bg-brand-600 px-4 py-2 text-sm font-bold text-white transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2"
            >
              {isFirst ? "Take the tour" : isLast ? "Done, start exploring" : "Next"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
