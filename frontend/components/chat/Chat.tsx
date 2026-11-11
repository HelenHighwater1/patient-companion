"use client";

import { useEffect, useRef, useState } from "react";
import { fetchPrepSheet, streamChat, streamUpload } from "@/lib/api";
import type {
  ConversationTurn,
  Evidence,
  Message,
  PrepSheet,
  ReadingLevel,
  RetrievalTrace,
  SampleDocument,
  Source,
  ServerEvent,
  Stage,
} from "@/lib/types";
import { AnswerMessage } from "./AnswerMessage";
import { CardStack } from "./CardStack";
import { ChatInput } from "./ChatInput";
import { TypingIndicator } from "./TypingIndicator";
import { ReadingLevelToggle } from "../ReadingLevelToggle";
import { PrepSheetModal } from "../PrepSheetModal";

let nextId = 1;
const uid = () => `m${nextId++}`;

export interface ShowEvidenceOptions {
  marker?: number;
  /** Open the evidence drawer on narrow screens. */
  reveal?: boolean;
  /** Only replace the panel if it's already showing this message. */
  onlyIfActive?: boolean;
}

interface Props {
  documentToLoad: SampleDocument | null;
  onDocumentLoaded: () => void;
  /** Wide layout: citations open the side evidence panel instead of the inline list. */
  wide: boolean;
  activeEvidenceId: string | null;
  hoveredSourceKey: string | null;
  onEvidence: (e: Evidence, opts?: ShowEvidenceOptions) => void;
}

function evidenceFrom(m: Message): Evidence | null {
  if (m.role !== "assistant") return null;
  if (m.kind === "answer") {
    return {
      messageId: m.id,
      question: m.question,
      status: "done",
      trace: m.trace,
      sources: m.sources,
      citations: m.citations,
      flaggedGaps: m.flaggedGaps,
    };
  }
  if (m.kind === "refusal" && m.trace) {
    return {
      messageId: m.id,
      question: m.question ?? "",
      status: "refused",
      trace: m.trace,
      sources: m.sources ?? [],
      citations: [],
      flaggedGaps: [],
    };
  }
  return null;
}

export function Chat({
  documentToLoad,
  onDocumentLoaded,
  wide,
  activeEvidenceId,
  hoveredSourceKey,
  onEvidence,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [stage, setStage] = useState<Stage | null>(null);
  const [busy, setBusy] = useState(false);
  const [readingLevel, setReadingLevel] = useState<ReadingLevel>("standard");
  const [documentContext, setDocumentContext] = useState<string | null>(null);
  const [patientConcerns, setPatientConcerns] = useState<string[]>([]);
  const [history, setHistory] = useState<ConversationTurn[]>([]);
  const [prepSheet, setPrepSheet] = useState<PrepSheet | null>(null);
  const [prepLoading, setPrepLoading] = useState(false);
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, stage]);

  // Load a sample document when selected from the sidebar
  useEffect(() => {
    if (documentToLoad) {
      loadSampleDocument(documentToLoad);
      onDocumentLoaded();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documentToLoad]);

  const appendMessage = (m: Message) => setMessages((ms) => [...ms, m]);
  const patchMessage = (id: string, patch: (m: Message) => Message) =>
    setMessages((ms) => ms.map((m) => (m.id === id ? patch(m) : m)));

  /** Handle SSE events for the document-intake flow. */
  const handleDocEvent = (msgId: string, e: ServerEvent) => {
    if (e.type === "status") setStage(e.stage);
    if (e.type === "card") {
      patchMessage(msgId, (m) =>
        m.role === "assistant" && m.kind === "cards"
          ? { ...m, cards: [...m.cards, { key: e.key, label: e.label, body: e.body }] }
          : m,
      );
    }
    if (e.type === "concerns") {
      patchMessage(msgId, (m) =>
        m.role === "assistant" && m.kind === "cards" ? { ...m, concerns: e.items } : m,
      );
    }
    if (e.type === "done") {
      setStage(null);
      setBusy(false);
      patchMessage(msgId, (m) =>
        m.role === "assistant" && m.kind === "cards" ? { ...m, complete: true } : m,
      );
      if (e.document_context) setDocumentContext(e.document_context);
      if (e.patient_concerns) setPatientConcerns(e.patient_concerns);
    }
  };

  const startDocumentStream = (
    run: (onEvent: (e: ServerEvent) => void) => Promise<void>,
    userLabel: string,
  ) => {
    setBusy(true);
    appendMessage({ id: uid(), role: "user", text: userLabel });
    const msgId = uid();
    appendMessage({
      id: msgId,
      role: "assistant",
      kind: "cards",
      cards: [],
      concerns: [],
      complete: false,
    });
    run((e) => handleDocEvent(msgId, e)).catch((err) => {
      setStage(null);
      setBusy(false);
      patchMessage(msgId, () => ({
        id: msgId,
        role: "assistant",
        kind: "error",
        text: `Something went wrong reading that document. ${err instanceof Error ? err.message : ""} The demo API may still be waking up after inactivity — try again in a few seconds.`,
      }));
    });
  };

  const loadSampleDocument = (doc: SampleDocument) => {
    if (busy) return;
    setActiveDoc(doc.filename);
    startDocumentStream(
      (onEvent) =>
        streamChat(
          {
            inputType: "document",
            filename: doc.filename,
            conversationHistory: history,
            readingLevel,
          },
          onEvent,
        ),
      `Please walk me through "${doc.title}".`,
    );
  };

  const uploadFile = (file: File) => {
    if (busy) return;
    setActiveDoc(file.name);
    startDocumentStream(
      (onEvent) => streamUpload(file, onEvent),
      `Uploaded document: ${file.name}`,
    );
  };

  const sendQuestion = (text: string) => {
    if (busy) return;
    const question = text.trim();
    if (!question) return;
    setBusy(true);
    appendMessage({ id: uid(), role: "user", text: question });
    const msgId = uid();
    let trace: RetrievalTrace | null = null;
    let retrieved: Source[] = [];
    streamChat(
      {
        inputType: "question",
        message: question,
        conversationHistory: history,
        documentContext,
        readingLevel,
      },
      (e) => {
        if (e.type === "status") setStage(e.stage);
        if (e.type === "retrieval") {
          trace = {
            query_variants: e.query_variants ?? [],
            refused: e.refused,
            refusal_reason: e.refusal_reason,
            counts: e.counts,
            gate: e.gate,
            latencies_ms: e.latencies_ms ?? {},
          };
          retrieved = e.sources ?? [];
          onEvidence({
            messageId: msgId,
            question,
            status: e.refused ? "refused" : "answering",
            trace,
            sources: retrieved,
            citations: [],
            flaggedGaps: [],
          });
        }
        if (e.type === "refusal") {
          appendMessage({
            id: msgId,
            role: "assistant",
            kind: "refusal",
            text: e.message,
            question,
            trace,
            sources: retrieved,
          });
        }
        if (e.type === "answer") {
          const answer: Message = {
            id: msgId,
            role: "assistant",
            kind: "answer",
            question,
            trace,
            text: e.patient_response ?? "",
            questions: e.doctor_questions ?? [],
            citations: e.citations ?? [],
            sources: e.sources ?? [],
            flaggedGaps: e.flagged_gaps ?? [],
            disclaimer: e.disclaimer ?? "",
          };
          appendMessage(answer);
          const ev = evidenceFrom(answer);
          if (ev) onEvidence(ev, { onlyIfActive: true });
          setHistory((h) => [...h, { question, patient_response: e.patient_response }].slice(-10));
        }
        if (e.type === "done") {
          setStage(null);
          setBusy(false);
        }
      },
    ).catch((err) => {
      if (trace) {
        onEvidence(
          {
            messageId: msgId,
            question,
            status: "error",
            trace,
            sources: retrieved,
            citations: [],
            flaggedGaps: [],
          },
          { onlyIfActive: true },
        );
      }
      appendMessage({
        id: msgId,
        role: "assistant",
        kind: "error",
        text: `Something went wrong. ${err instanceof Error ? err.message : "Please try again."} The demo API may still be waking up after inactivity — try again in a few seconds.`,
      });
      setStage(null);
      setBusy(false);
    });
  };

  const openPrepSheet = async () => {
    setPrepLoading(true);
    try {
      const sheet = await fetchPrepSheet({
        conversationHistory: history,
        documentContext: documentContext ?? "",
        patientConcerns,
        readingLevel,
      });
      setPrepSheet(sheet);
    } catch (err) {
      appendMessage({
        id: uid(),
        role: "assistant",
        kind: "error",
        text: `Couldn't build the prep sheet. ${err instanceof Error ? err.message : ""}`,
      });
    } finally {
      setPrepLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-warm-100 px-5 py-3">
        <ReadingLevelToggle value={readingLevel} onChange={setReadingLevel} />
        <button
          onClick={openPrepSheet}
          disabled={prepLoading || (history.length === 0 && !documentContext)}
          title="Build a printable sheet for your appointment"
          className="rounded-full bg-ochre-100 px-4 py-1.5 text-xs font-bold text-ochre-900 transition-colors hover:bg-ochre-200 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {prepLoading ? "Building…" : "Prepare for appointment"}
        </button>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
        {messages.length === 0 && !busy && (
          <div className="mx-auto mt-10 max-w-md rounded-3xl bg-warm-50 p-6 text-center">
            <p className="mb-2 font-display text-2xl font-bold text-warm-900">Where would you like to start?</p>
            <p className="text-sm leading-relaxed text-warm-700">
              Load a fictional sample document from the left, drag a file into the box below,
              or ask a question about ALS care.
            </p>
          </div>
        )}

        {messages.map((m) => {
          if (m.role === "user") {
            return (
              <div key={m.id} className="flex justify-end">
                <div className="max-w-[85%] rounded-3xl rounded-br-md bg-brand-600 px-4 py-2.5 text-sm text-white shadow-float">
                  {m.text}
                </div>
              </div>
            );
          }
          return (
            <div key={m.id} className="flex justify-start">
              <div className="max-w-[92%]">
                {m.kind === "cards" && (
                  <CardStack cards={m.cards} concerns={m.concerns} pending={!m.complete} />
                )}
                {m.kind === "answer" && (
                  <AnswerMessage
                    text={m.text}
                    questions={m.questions}
                    citations={m.citations}
                    sources={m.sources}
                    flaggedGaps={m.flaggedGaps}
                    disclaimer={m.disclaimer}
                    onAskQuestion={sendQuestion}
                    wide={wide}
                    active={m.id === activeEvidenceId}
                    hoveredSourceKey={m.id === activeEvidenceId ? hoveredSourceKey : null}
                    onShowEvidence={(marker) => {
                      const ev = evidenceFrom(m);
                      if (ev) onEvidence(ev, { marker, reveal: true });
                    }}
                  />
                )}
                {(m.kind === "refusal" || m.kind === "error") && (
                  <div className="rounded-3xl rounded-bl-md bg-warm-50 px-4 py-3 text-sm leading-relaxed text-warm-800">
                    {m.text}
                    {m.kind === "refusal" && m.trace && (
                      <button
                        onClick={() => {
                          const ev = evidenceFrom(m);
                          if (ev) onEvidence(ev, { reveal: true });
                        }}
                        className="mt-2 block text-xs font-bold text-brand-700 hover:underline"
                      >
                        See what was searched →
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {busy && <TypingIndicator stage={stage} />}
      </div>

      <div className="p-3">
        <ChatInput disabled={busy} onSend={sendQuestion} onUpload={uploadFile} />
      </div>

      {prepSheet && (
        <PrepSheetModal
          sheet={prepSheet}
          documentName={activeDoc}
          onClose={() => setPrepSheet(null)}
        />
      )}
    </div>
  );
}
