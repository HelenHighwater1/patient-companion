/** Shared types matching the backend's SSE event contract. */

export type ReadingLevel = "gentle" | "standard" | "detailed";

export interface CardBody {
  key: string;
  label: string;
  body: string | string[];
}

export interface Citation {
  marker: number;
  claim: string;
  source: string;
  title: string | null;
  url: string | null;
}

export interface Source {
  source: string;
  chunk_index: number;
  title: string | null;
  url: string | null;
}

export type ServerEvent =
  | { type: "status"; stage: Stage }
  | { type: "card"; index: number; key: string; label: string; body: string | string[] }
  | { type: "concerns"; items: string[] }
  | { type: "refusal"; message: string; reason?: string }
  | {
      type: "answer";
      patient_response: string;
      doctor_questions: string[];
      citations: Citation[];
      sources: Source[];
      flagged_gaps: string[];
      confidence: { claim: string; score: number }[];
      disclaimer: string;
    }
  | { type: "done"; document_context?: string; patient_concerns?: string[] };

export type Stage = "reading" | "searching" | "answering" | "checking" | "rewriting";

export type Message =
  | { id: string; role: "user"; text: string }
  | {
      id: string;
      role: "assistant";
      kind: "cards";
      cards: CardBody[];
      concerns: string[];
      complete: boolean;
    }
  | {
      id: string;
      role: "assistant";
      kind: "answer";
      text: string;
      questions: string[];
      citations: Citation[];
      sources: Source[];
      flaggedGaps: string[];
      disclaimer: string;
    }
  | { id: string; role: "assistant"; kind: "refusal" | "error"; text: string };

export interface ConversationTurn {
  question: string;
  patient_response: string;
}

export interface SampleDocument {
  filename: string;
  title: string;
  file_type: string;
}

export interface PrepSheet {
  document_summary: string;
  your_questions: string[];
  suggested_questions: string[];
  topics_to_raise: string[];
  key_terms: { term: string; definition: string }[];
}
