// View model của hội thoại hỏi đáp (T-306 §3, SDD §3.4.1).

export type AnswerPhase =
  "pending" | "streaming" | "complete" | "failed" | "incomplete";
export type AnswerType = "answered" | "partial" | "not_found";

export type CitationVM = {
  index: number; // khớp [n] trong markdown
  documentId: string;
  documentName: string;
  pageStart?: number | null;
  pageEnd?: number | null;
};

export type AnswerVM = {
  id: string;
  phase: AnswerPhase;
  type?: AnswerType;
  markdown: string;
  citations: CitationVM[];
  latencyMs?: number;
  uncited?: boolean;
  errorCode?: string;
  retryAfterSeconds?: number;
};

export type UserMessage = {
  kind: "user";
  id: string;
  text: string;
};

export type AnswerMessage = {
  kind: "answer";
  answer: AnswerVM;
};

export type ChatMessage = UserMessage | AnswerMessage;

export type ComposerDisabledReason =
  "offline" | "no_docs" | "all_processing" | "all_failed" | "awaiting_answer";
