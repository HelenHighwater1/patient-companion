/** Shared types matching the backend's SSE event contract. */

export type ReadingLevel = "gentle" | "standard" | "detailed";

export interface CardBody {
  key: string;
  label: string;
  body: string | string[];
}

export interface Grounding {
  /** False when the cited passage wasn't among the retrieved chunks, so nothing was compared. */
  checked: boolean;
  /** Embedding cosine between the claim and its cited passage. */
  cosine: number | null;
  flagged: boolean;
  /** LLM judge: 1 = supported, 2 = partial, 3 = unsupported. */
  judge_score: number | null;
}

export interface Citation {
  marker: number;
  claim: string;
  source: string;
  chunk_index?: number;
  title: string | null;
  url: string | null;
  grounding?: Grounding;
}

export interface Source {
  source: string;
  chunk_index: number;
  title: string | null;
  url: string | null;
  section?: string | null;
  section_path?: string | null;
  year?: number | null;
  source_type?: string | null;
  excerpt?: string;
  relevance?: number;
  dense_cosine?: number | null;
  fusion_score?: number | null;
  rerank_score?: number | null;
  /** Set on answer events: whether the answer cites this passage, and with which markers. */
  cited?: boolean;
  markers?: number[];
}

export interface RetrievalGate {
  method: "dense_cosine" | "rerank_margin";
  value: number;
  threshold: number;
  /** Rerank only: the top passage's score. A non-negative score passes even with a small margin. */
  top_score?: number;
  passed: boolean;
}

export interface RetrievalTrace {
  query_variants: string[];
  refused: boolean;
  refusal_reason: string | null;
  counts: { dense: number; bm25: number; fused: number; returned: number };
  gate: RetrievalGate | null;
  latencies_ms: Record<string, number>;
}

/** Everything the evidence panel shows for one question. */
export interface Evidence {
  messageId: string;
  question: string;
  status: "answering" | "done" | "refused" | "error";
  trace: RetrievalTrace | null;
  sources: Source[];
  citations: Citation[];
  flaggedGaps: string[];
}

export interface CorpusSource {
  source: string;
  title: string;
  url: string | null;
  source_type: string | null;
  year: number | null;
  chunks: number;
}

export interface CorpusSummary {
  disease: string;
  label: string;
  chunk_count: number;
  built_at: string | null;
  embedding_model: string | null;
  sources: CorpusSource[];
}

export type ServerEvent =
  | { type: "status"; stage: Stage }
  | { type: "card"; index: number; key: string; label: string; body: string | string[] }
  | { type: "concerns"; items: string[] }
  | ({ type: "retrieval"; sources: Source[] } & RetrievalTrace)
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
      question: string;
      trace: RetrievalTrace | null;
      text: string;
      questions: string[];
      citations: Citation[];
      sources: Source[];
      flaggedGaps: string[];
      disclaimer: string;
    }
  | {
      id: string;
      role: "assistant";
      kind: "refusal" | "error";
      text: string;
      question?: string;
      trace?: RetrievalTrace | null;
      sources?: Source[];
    };

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
