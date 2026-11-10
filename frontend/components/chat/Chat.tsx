"use client";

import { useEffect, useRef, useState } from "react";
import { fetchPrepSheet, streamChat, streamUpload } from "@/lib/api";
import type {
  ConversationTurn,
  Message,
  PrepSheet,
  ReadingLevel,
  SampleDocument,
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

interface Props {
  documentToLoad: SampleDocument | null;
  onDocumentLoaded: () => void;
}

export function Chat({ documentToLoad, onDocumentLoaded }: Props) {
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
    appendMessage({ id: msgId, role: "assistant", kind: "cards", cards: [], concerns: [] });
    run((e) => handleDocEvent(msgId, e)).catch((err) => {
      setStage(null);
      setBusy(false);
      patchMessage(msgId, () => ({
        id: msgId,
        role: "assistant",
        kind: "error",
        text: `Something went wrong reading that document. ${err instanceof Error ? err.message : ""}`,
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
        if (e.type === "refusal") {
          appendMessage({ id: msgId, role: "assistant", kind: "refusal", text: e.message });
        }
        if (e.type === "answer") {
          appendMessage({
            id: msgId,
            role: "assistant",
            kind: "answer",
            text: e.patient_response ?? "",
            questions: e.doctor_questions ?? [],
            citations: e.citations ?? [],
            sources: e.sources ?? [],
            flaggedGaps: e.flagged_gaps ?? [],
            disclaimer: e.disclaimer ?? "",
          });
          setHistory((h) => [...h, { question, patient_response: e.patient_response }].slice(-10));
        }
        if (e.type === "done") {
          setStage(null);
          setBusy(false);
        }
      },
    ).catch((err) => {
      appendMessage({
        id: msgId,
        role: "assistant",
        kind: "error",
        text: `Something went wrong. ${err instanceof Error ? err.message : "Please try again."}`,
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
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-warm-200 px-4 py-2">
        <ReadingLevelToggle value={readingLevel} onChange={setReadingLevel} />
        <button
          onClick={openPrepSheet}
          disabled={prepLoading || (history.length === 0 && !documentContext)}
          title="Build a printable sheet for your appointment"
          className="rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-800 transition-colors hover:bg-brand-100 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {prepLoading ? "Building…" : "Prepare for appointment"}
        </button>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-5">
        {messages.length === 0 && !busy && (
          <div className="mx-auto mt-10 max-w-md rounded-2xl bg-white p-6 text-center shadow-sm ring-1 ring-warm-200">
            <p className="mb-2 text-base font-medium text-warm-900">Where would you like to start?</p>
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
                <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-sm text-white shadow-sm">
                  {m.text}
                </div>
              </div>
            );
          }
          return (
            <div key={m.id} className="flex justify-start">
              <div className="max-w-[92%]">
                {m.kind === "cards" && <CardStack cards={m.cards} concerns={m.concerns} />}
                {m.kind === "answer" && (
                  <AnswerMessage
                    text={m.text}
                    questions={m.questions}
                    citations={m.citations}
                    sources={m.sources}
                    flaggedGaps={m.flaggedGaps}
                    disclaimer={m.disclaimer}
                    onAskQuestion={sendQuestion}
                  />
                )}
                {(m.kind === "refusal" || m.kind === "error") && (
                  <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-sm leading-relaxed text-warm-800 shadow-sm ring-1 ring-warm-200">
                    {m.text}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {busy && <TypingIndicator stage={stage} />}
      </div>

      <div className="border-t border-warm-200 p-3">
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
