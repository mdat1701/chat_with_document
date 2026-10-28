import { Component, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  apiFetch,
  ApiError,
  streamQuestion,
  subscribeDocumentEvents,
  type DocumentEventPayload,
} from "@shared/api/client";
import { track } from "@shared/analytics/client";
import { useAppConfig } from "@shared/config";
import { registerComposerSource, restoreDraft, clearDraft } from "@features/auth/draft";
import { Banner, Skeleton, useToast } from "@shared/ui";
import { uiText } from "@shared/i18n/messages.vi";
import { AnswerMessage } from "./AnswerMessage";
import { Composer } from "./Composer";
import type { AnswerVM, ChatMessage, ComposerDisabledReason } from "./types";
import "./chat.css";

type DocumentSummary = { id: string; status: string };

function detectLanguage(value: string): "vi" | "en" | "other" {
  if (value.trim().length < 10) return "other";
  if (/[ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặ]/.test(value)) return "vi";
  return /\b(the|what|how|when|where|is|are)\b/i.test(value) ? "en" : "other";
}

function makeId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/** T-307 §5.9: lỗi JS trong khu vực chat không được làm sập phần còn lại của trang. */
class ChatErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <Banner tone="danger" data-testid="chat-crash-banner">
          Đã có lỗi xảy ra trong khu vực hỏi đáp. Vui lòng tải lại trang.
        </Banner>
      );
    }
    return this.props.children;
  }
}

export function ChatPage() {
  return (
    <ChatErrorBoundary>
      <ChatPageInner />
    </ChatErrorBoundary>
  );
}

function ChatPageInner() {
  const { config } = useAppConfig();
  const { showToast } = useToast();
  // AC-001.3: khôi phục bản nháp câu hỏi đã lưu khi phiên trước hết hạn
  // (xem features/auth/draft.ts), rồi xóa khỏi sessionStorage ngay sau khi đọc.
  const [draft, setDraft] = useState(() => restoreDraft() ?? "");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [online, setOnline] = useState(() => navigator.onLine);
  const [liveAnnouncement, setLiveAnnouncement] = useState("");

  const conversationIdRef = useRef<string>();
  const questionByAnswerId = useRef(new Map<string, string>());
  const readyDocCountRef = useRef(0);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    clearDraft();
  }, []);

  // Cho interceptor 401 toàn cục (shared/api/client.ts → setUnauthorizedHandler)
  // đọc nội dung đang soạn mà không cần shared/api phụ thuộc ngược vào features/chat.
  useEffect(() => {
    registerComposerSource(() => draft);
    return () => registerComposerSource(null);
  }, [draft]);

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiFetch<DocumentSummary[]>("/documents")
      .then((docs) => {
        if (!cancelled) setDocuments(docs);
      })
      .catch(() => {
        if (!cancelled) setDocuments([]);
      })
      .finally(() => {
        if (!cancelled) setDocumentsLoading(false);
      });
    const unsubscribe = subscribeDocumentEvents((payload: DocumentEventPayload) => {
      setDocuments((current) => {
        const exists = current.some((doc) => doc.id === payload.id);
        if (!exists) return current;
        return current.map((doc) => (doc.id === payload.id ? { ...doc, status: payload.status } : doc));
      });
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    const container = listRef.current;
    if (!container) return;
    const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
    if (distanceToBottom < 120) container.scrollTop = container.scrollHeight;
  }, [messages]);

  const readyDocCount = useMemo(() => documents.filter((d) => d.status === "ready").length, [documents]);
  readyDocCountRef.current = readyDocCount;
  const noDocs = documents.length === 0;
  const allProcessing = documents.length > 0 && documents.every((d) => d.status === "processing");
  const allFailed = documents.length > 0 && documents.every((d) => d.status === "failed");
  const awaitingAnswer = messages.some(
    (m) => m.kind === "answer" && (m.answer.phase === "pending" || m.answer.phase === "streaming"),
  );

  // SDD §3.7.3 — thứ tự ưu tiên #1-5, điều kiện trên thắng điều kiện dưới.
  const disabledReason: ComposerDisabledReason | undefined = !online
    ? "offline"
    : noDocs
      ? "no_docs"
      : allProcessing
        ? "all_processing"
        : allFailed
          ? "all_failed"
          : awaitingAnswer
            ? "awaiting_answer"
            : undefined;

  function updateAnswer(answerId: string, updater: (a: AnswerVM) => AnswerVM) {
    setMessages((current) =>
      current.map((m) =>
        m.kind === "answer" && m.answer.id === answerId ? { kind: "answer", answer: updater(m.answer) } : m,
      ),
    );
  }

  async function ensureConversationId(): Promise<string> {
    if (conversationIdRef.current) return conversationIdRef.current;
    const { conversation_id } = await apiFetch<{ conversation_id: string }>("/conversations", { method: "POST" });
    conversationIdRef.current = conversation_id;
    return conversation_id;
  }

  async function runQuestion(answerId: string, text: string) {
    let conversationId: string;
    try {
      conversationId = await ensureConversationId();
    } catch (err) {
      const code = err instanceof ApiError ? err.body.code : "ANSWER_NETWORK";
      track("answer_failed", { error_code: code });
      updateAnswer(answerId, (a) => ({ ...a, phase: "failed", errorCode: code }));
      return;
    }

    let hasDelta = false;
    await streamQuestion(conversationId, text, (event) => {
      switch (event.type) {
        case "meta":
          break;
        case "delta":
          hasDelta = true;
          updateAnswer(answerId, (a) => ({ ...a, phase: "streaming", markdown: a.markdown + event.text }));
          break;
        case "citations":
          updateAnswer(answerId, (a) => ({
            ...a,
            citations: event.items.map((item, i) => ({
              index: item.index ?? i + 1,
              documentId: item.document_id,
              documentName: item.document_name ?? "Tài liệu",
              pageStart: item.page_start,
              pageEnd: item.page_end,
            })),
          }));
          break;
        case "done":
          // T-404 §5.4: `answer_rendered` đã được backend phát trực tiếp
          // (conversations.py, ngay sau `event: done`) để `latency_ms` chính
          // xác tuyệt đối — FE **không** phát lại sự kiện này, tránh đếm
          // trùng trong `analytics_event`.
          updateAnswer(answerId, (a) => ({
            ...a,
            phase: "complete",
            type: event.answerType as AnswerVM["type"],
            latencyMs: event.latencyMs,
            uncited: event.uncited,
          }));
          setLiveAnnouncement(uiText.answeredLiveRegion);
          break;
        case "error": {
          // NE-07: interceptor toàn cục (shared/api/client.ts → setUnauthorizedHandler)
          // đã lưu nháp và đặt lại phiên; App.tsx tự điều hướng /login khi user=null,
          // nên ở đây chỉ cần tránh ghi nhận `answer_failed` trùng cho trường hợp này.
          const phase = hasDelta && event.code === "ANSWER_INTERRUPTED" ? "incomplete" : "failed";
          if (event.code !== "SESSION_EXPIRED") {
            track("answer_failed", { error_code: event.code });
          }
          updateAnswer(answerId, (a) => ({
            ...a,
            phase,
            errorCode: event.code,
            retryAfterSeconds: event.retryAfterSeconds,
          }));
          break;
        }
        default:
          break;
      }
    });
  }

  function submitQuestion(text: string) {
    const trimmed = text.trim();
    if (!trimmed || disabledReason) return;
    if (trimmed.length > config.max_question_length) return;
    const userId = makeId("u");
    const answerId = makeId("a");
    questionByAnswerId.current.set(answerId, trimmed);
    // Optimistic (IX-03): thêm tin nhắn + TypingIndicator ngay trong cùng frame.
    setMessages((current) => [
      ...current,
      { kind: "user", id: userId, text: trimmed },
      { kind: "answer", answer: { id: answerId, phase: "pending", markdown: "", citations: [] } },
    ]);
    setDraft("");
    clearDraft();
    track("question_submitted", {
      question_length: trimmed.length,
      language: detectLanguage(trimmed),
      ready_doc_count: readyDocCountRef.current,
    });
    void runQuestion(answerId, trimmed);
  }

  function retryAnswer(answerId: string, context: string) {
    const text = questionByAnswerId.current.get(answerId);
    if (!text) return;
    track("retry_clicked", { context });
    showToast({ title: uiText.resendLabel, tone: "neutral", duration: 2500 });
    updateAnswer(answerId, (a) => ({
      ...a,
      phase: "pending",
      markdown: "",
      citations: [],
      type: undefined,
      errorCode: undefined,
      uncited: undefined,
      retryAfterSeconds: undefined,
    }));
    void runQuestion(answerId, text);
  }

  const noMessagesYet = messages.length === 0;
  const showExamples = noMessagesYet && !disabledReason;

  return (
    <section aria-label="Hỏi đáp" className="chat-page">
      <h2>Hỏi về tài liệu</h2>
      <div aria-live="polite" className="sr-only" data-testid="answer-announcer">
        {liveAnnouncement}
      </div>

      {documentsLoading ? (
        <Skeleton height={20} width={180} data-testid="chat-loading-skeleton" />
      ) : (
        <div ref={listRef} className="chat-message-list" aria-live="polite" data-testid="message-list">
          {noMessagesYet && (
            <p className="chat-typing-indicator" data-testid="chat-empty-hint">
              {uiText.answerPending}
            </p>
          )}
          {messages.map((message) =>
            message.kind === "user" ? (
              <div key={message.id} className="chat-message--user" data-testid="user-message">
                {message.text}
              </div>
            ) : (
              <AnswerMessage
                key={message.answer.id}
                answer={message.answer}
                readyDocCount={readyDocCount}
                showPageNumbers={config.features.citation_page_numbers}
                onRetry={() => retryAnswer(message.answer.id, message.answer.phase)}
              />
            ),
          )}
        </div>
      )}

      {showExamples && (
        <div className="chat-examples" data-testid="chat-examples">
          <p>{uiText.composerExamplesTitle}</p>
          <ul className="chat-examples__list">
            {uiText.composerExamples.map((example) => (
              <li key={example}>
                <button type="button" onClick={() => setDraft(example)}>
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Composer
        value={draft}
        onChange={setDraft}
        onSubmit={() => submitQuestion(draft)}
        maxLength={config.max_question_length}
        disabledReason={disabledReason}
      />
    </section>
  );
}
