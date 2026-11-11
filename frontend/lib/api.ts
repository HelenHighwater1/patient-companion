/** API client: REST endpoints + SSE stream parsing. */

import type {
  ConversationTurn,
  PrepSheet,
  ReadingLevel,
  SampleDocument,
  ServerEvent,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function listDocuments(): Promise<SampleDocument[]> {
  const res = await fetch(`${API_URL}/api/documents`);
  if (!res.ok) throw new Error(`Documents request failed (${res.status})`);
  return res.json();
}

export async function fetchDocumentText(filename: string): Promise<string> {
  const res = await fetch(`${API_URL}/api/documents/${encodeURIComponent(filename)}/text`);
  if (!res.ok) throw new Error("Could not load document text");
  return res.text();
}

export function documentUrl(filename: string): string {
  return `${API_URL}/api/documents/${encodeURIComponent(filename)}`;
}

/** Parse a `data: {...}\n\n` SSE stream into events. Exported for tests. */
export function parseSSEChunk(buffer: string): { events: ServerEvent[]; rest: string } {
  const events: ServerEvent[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  for (const part of parts) {
    const line = part.trim();
    if (!line.startsWith("data: ")) continue;
    try {
      events.push(JSON.parse(line.slice(6)));
    } catch {
      // ignore malformed frames
    }
  }
  return { events, rest };
}

async function streamEvents(
  path: string,
  init: RequestInit,
  onEvent: (e: ServerEvent) => void,
): Promise<void> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Request failed (${res.status}): ${detail.slice(0, 200)}`);
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error("Streaming not supported in this browser");
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const { events, rest } = parseSSEChunk(buffer);
    buffer = rest;
    events.forEach(onEvent);
  }
}

export interface ChatPayload {
  message?: string;
  inputType: "question" | "document";
  conversationHistory: ConversationTurn[];
  documentContext?: string | null;
  filename?: string;
  documentText?: string;
  readingLevel: ReadingLevel;
}

export async function streamChat(
  payload: ChatPayload,
  onEvent: (e: ServerEvent) => void,
): Promise<void> {
  await streamEvents(
    "/api/chat",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: payload.message ?? null,
        input_type: payload.inputType,
        conversation_history: payload.conversationHistory,
        document_context: payload.documentContext ?? null,
        document_text: payload.documentText ?? null,
        filename: payload.filename ?? null,
        reading_level: payload.readingLevel,
      }),
    },
    onEvent,
  );
}

export async function streamUpload(
  file: File,
  onEvent: (e: ServerEvent) => void,
): Promise<void> {
  const form = new FormData();
  form.append("file", file);
  await streamEvents("/api/chat/upload", { method: "POST", body: form }, onEvent);
}

export async function fetchPrepSheet(body: {
  conversationHistory: ConversationTurn[];
  documentContext: string;
  patientConcerns: string[];
  readingLevel: ReadingLevel;
}): Promise<PrepSheet> {
  const res = await fetch(`${API_URL}/api/prep-sheet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_history: body.conversationHistory,
      document_context: body.documentContext,
      patient_concerns: body.patientConcerns,
      reading_level: body.readingLevel,
    }),
  });
  if (!res.ok) throw new Error("Could not build the prep sheet");
  return res.json();
}
