import { Fragment, isValidElement, cloneElement, useEffect, useState, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import { Banner, Button } from "@shared/ui";
import { messages as errorMessages, type ErrorCode, uiText } from "@shared/i18n/messages.vi";
import { CitationChip, CitationRef } from "./CitationChip";
import type { AnswerVM, CitationVM } from "./types";

// IR-04: chỉ cho phép các thẻ văn bản cơ bản, không thuộc tính (chặn
// `script`, `iframe`, `img`, `a href` tùy ý, mọi thuộc tính `on*`).
const sanitizeSchema = {
  ...defaultSchema,
  tagNames: ["p", "strong", "em", "ul", "ol", "li", "code", "br"],
  attributes: {},
};

type HighlightCtx = {
  citationsByIndex: Map<number, CitationVM>;
  highlightedIndex: number | null;
  onHighlight: (index: number | null) => void;
};

function splitCitationTokens(text: string, ctx: HighlightCtx, keyPrefix: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const regex = /\[(\d+)\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) parts.push(text.slice(lastIndex, match.index));
    const idx = Number(match[1]);
    const citation = ctx.citationsByIndex.get(idx);
    parts.push(
      <CitationRef
        key={`${keyPrefix}-${i++}`}
        index={idx}
        citation={citation}
        highlighted={ctx.highlightedIndex === idx}
        onHighlight={ctx.onHighlight}
      />,
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts.length ? parts : [text];
}

/** Duyệt children của react-markdown, thay `[n]` bằng `CitationRef` (UX-04). */
function renderWithCitationRefs(node: ReactNode, ctx: HighlightCtx, keyPrefix = "c"): ReactNode {
  if (typeof node === "string") return splitCitationTokens(node, ctx, keyPrefix);
  if (Array.isArray(node)) {
    return node.map((child, i) => (
      <Fragment key={`${keyPrefix}-f-${i}`}>{renderWithCitationRefs(child, ctx, `${keyPrefix}-${i}`)}</Fragment>
    ));
  }
  if (isValidElement<{ children?: ReactNode }>(node)) {
    return cloneElement(node, undefined, renderWithCitationRefs(node.props.children, ctx, keyPrefix));
  }
  return node;
}

function markdownComponents(ctx: HighlightCtx): Components {
  const wrap =
    (Tag: "p" | "li" | "strong" | "em") =>
    ({ children }: { children?: ReactNode }) =>
      <Tag>{renderWithCitationRefs(children, ctx)}</Tag>;
  return { p: wrap("p"), li: wrap("li"), strong: wrap("strong"), em: wrap("em") };
}

export type AnswerMessageProps = {
  answer: AnswerVM;
  readyDocCount: number;
  showPageNumbers: boolean;
  onRetry: () => void;
};

/** Hiển thị một lượt câu trả lời theo `phase` (T-306 §3 bảng 7 dòng, SDD §3.7.2). */
export function AnswerMessage({ answer, readyDocCount, showPageNumbers, onRetry }: AnswerMessageProps) {
  const [highlightedIndex, setHighlightedIndex] = useState<number | null>(null);
  const citationsByIndex = new Map(answer.citations.map((c) => [c.index, c]));
  const ctx: HighlightCtx = { citationsByIndex, highlightedIndex, onHighlight: setHighlightedIndex };

  if (answer.phase === "pending") {
    return (
      <div className="chat-answer chat-answer--pending" data-testid="answer-message" data-phase="pending">
        <span className="chat-typing-indicator" data-testid="typing-indicator">
          {uiText.typingIndicator(readyDocCount)}
        </span>
      </div>
    );
  }

  if (answer.phase === "failed") {
    return (
      <div className="chat-answer chat-answer--failed" data-testid="answer-message" data-phase="failed">
        <ErrorMessage errorCode={answer.errorCode} retryAfterSeconds={answer.retryAfterSeconds} onRetry={onRetry} />
      </div>
    );
  }

  if (answer.phase === "complete" && answer.type === "not_found") {
    return (
      <div className="chat-answer chat-answer--not-found" data-testid="answer-message" data-phase="complete" data-answer-type="not_found">
        <NotFoundMessage />
      </div>
    );
  }

  const isIncomplete = answer.phase === "incomplete";
  const isComplete = answer.phase === "complete";
  const uncited = Boolean(answer.uncited) || (answer.type === "answered" && isComplete && answer.citations.length === 0);

  return (
    <div
      className={["chat-answer", isIncomplete ? "chat-answer--incomplete" : ""].filter(Boolean).join(" ")}
      data-testid="answer-message"
      data-phase={answer.phase}
      data-answer-type={answer.type}
    >
      <div className="chat-answer__body" data-testid="answer-markdown">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}
          components={markdownComponents(ctx)}
        >
          {answer.markdown}
        </ReactMarkdown>
        {answer.phase === "streaming" && (
          <span className="chat-cursor" aria-hidden="true" data-testid="streaming-cursor" />
        )}
      </div>

      {answer.phase === "complete" && answer.type === "partial" && (
        <p className="chat-answer__note" data-testid="partial-note">
          {uiText.answerPartialNote}
        </p>
      )}

      {isIncomplete && (
        <p className="chat-answer__note" data-testid="incomplete-note">
          {uiText.answerIncompleteNote}
        </p>
      )}

      {isComplete && uncited && (
        <Banner tone="warning" data-testid="uncited-warning">
          {uiText.answerUncitedWarning}
        </Banner>
      )}

      {/* IR-01: thẻ nguồn chỉ hiển thị khi phase = 'complete' (ẩn hoàn toàn khi incomplete/failed). */}
      {isComplete && answer.citations.length > 0 && (
        <ul className="chat-citation-list" data-testid="citation-list">
          {answer.citations.map((citation) => (
            <li key={`${citation.documentId}-${citation.index}`}>
              <CitationChip
                citation={citation}
                highlighted={highlightedIndex === citation.index}
                showPageNumbers={showPageNumbers}
                onHighlight={setHighlightedIndex}
              />
            </li>
          ))}
        </ul>
      )}

      {isComplete && typeof answer.latencyMs === "number" && (
        <p className="chat-answer__latency" data-testid="answer-latency">
          {uiText.answerLatency(answer.latencyMs / 1000)}
        </p>
      )}

      {isIncomplete && (
        <div className="chat-answer__actions">
          <Button variant="secondary" data-testid="retry-button" onClick={onRetry}>
            {uiText.retryLabel}
          </Button>
        </div>
      )}
    </div>
  );
}

function NotFoundMessage() {
  // UX-06: kiểu hiển thị riêng (nền xám nhạt, icon ℹ) — AC-014.4: tuyệt đối
  // không render CitationList dù citations rỗng hay không.
  return (
    <Banner tone="info" data-testid="not-found-message">
      <p>
        <span aria-hidden="true">ℹ </span>
        {uiText.notFoundTitle}
      </p>
      <p className="chat-answer__hint">{uiText.notFoundHint}</p>
    </Banner>
  );
}

function errorCodeMessage(code?: string): string {
  if (code && code in errorMessages) return errorMessages[code as ErrorCode];
  return errorMessages.SERVICE_BUSY;
}

function ErrorMessage({
  errorCode,
  retryAfterSeconds,
  onRetry,
}: {
  errorCode?: string;
  retryAfterSeconds?: number;
  onRetry: () => void;
}) {
  const [remaining, setRemaining] = useState(retryAfterSeconds ?? 0);

  useEffect(() => {
    setRemaining(retryAfterSeconds ?? 0);
    if (!retryAfterSeconds) return;
    const timer = setInterval(() => {
      setRemaining((value) => (value > 0 ? value - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [retryAfterSeconds, errorCode]);

  const actionLabel = errorCode === "ANSWER_NETWORK" ? uiText.resendLabel : uiText.retryLabel;
  const locked = remaining > 0;

  return (
    <Banner
      tone="danger"
      data-testid="error-message"
      actions={
        <Button variant="secondary" data-testid="retry-button" onClick={onRetry} disabled={locked}>
          {locked ? `${actionLabel} (${remaining}s)` : actionLabel}
        </Button>
      }
    >
      <span aria-hidden="true">⚠ </span>
      {errorCodeMessage(errorCode)}
    </Banner>
  );
}
