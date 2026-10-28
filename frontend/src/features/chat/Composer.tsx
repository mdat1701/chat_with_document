import {
  useEffect,
  useRef,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { Button, Tooltip } from "@shared/ui";
import { uiText } from "@shared/i18n/messages.vi";
import type { ComposerDisabledReason } from "./types";

const MAX_ROWS = 6;

const LOCK_TOOLTIP: Record<ComposerDisabledReason, string> = {
  offline: uiText.composerLockedOffline,
  no_docs: uiText.composerLockedNoReady,
  all_processing: uiText.composerLockedProcessing,
  all_failed: uiText.composerLockedAllFailed,
  awaiting_answer: uiText.composerLockedAwaitingAnswer,
};

export type ComposerProps = {
  value: string;
  onChange: (text: string) => void;
  onSubmit: () => void;
  maxLength: number;
  /** Điều kiện #1-5 của SDD §3.7.3 (đúng thứ tự ưu tiên); `undefined` = sẵn sàng. */
  disabledReason?: ComposerDisabledReason;
};

/** Ô nhập câu hỏi + bộ đếm ký tự + lời miễn trừ AI (T-305). */
export function Composer({
  value,
  onChange,
  onSubmit,
  maxLength,
  disabledReason,
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Điều kiện #1-4: khóa toàn bộ ô nhập. #5 (awaiting_answer): chỉ khóa nút Gửi,
  // vẫn gõ được.
  const fullyLocked =
    disabledReason !== undefined && disabledReason !== "awaiting_answer";
  const trimmed = value.trim();
  const overLength = value.length > maxLength;
  const sendDisabled = disabledReason !== undefined || !trimmed || overLength;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    const lineHeight = 24;
    const maxHeight = lineHeight * MAX_ROWS;
    textarea.style.height = `${Math.min(textarea.scrollHeight, maxHeight)}px`;
  }, [value]);

  useEffect(() => {
    // IX-02: `/` ngoài ô nhập đưa focus vào ô câu hỏi (bỏ qua nếu đang gõ ở input khác).
    const handler = (event: KeyboardEvent) => {
      if (event.key !== "/") return;
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      const isEditable =
        tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable;
      if (isEditable) return;
      event.preventDefault();
      textareaRef.current?.focus();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!sendDisabled) onSubmit();
    }
  };

  const textarea = (
    <textarea
      ref={textareaRef}
      id="question-input"
      data-testid="question-input"
      className="chat-composer__textarea"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={handleKeyDown}
      disabled={fullyLocked}
      placeholder={uiText.composerPlaceholder}
      rows={1}
      aria-describedby="chat-char-counter chat-ai-disclaimer"
      aria-invalid={overLength || undefined}
    />
  );

  return (
    <form
      className="chat-composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (!sendDisabled) onSubmit();
      }}
    >
      <label className="sr-only" htmlFor="question-input">
        {uiText.composerLabel}
      </label>
      {disabledReason ? (
        <Tooltip content={LOCK_TOOLTIP[disabledReason]}>{textarea}</Tooltip>
      ) : (
        textarea
      )}
      <div className="chat-composer__row">
        <span
          id="chat-char-counter"
          data-testid="char-counter"
          className={
            overLength
              ? "chat-char-counter chat-char-counter--danger"
              : "chat-char-counter"
          }
        >
          {uiText.composerCharCounter(value.length, maxLength)}
        </span>
        <Button
          type="submit"
          variant="primary"
          data-testid="send-button"
          disabled={sendDisabled}
        >
          {uiText.composerSubmit}
        </Button>
      </div>
      <p id="chat-ai-disclaimer" className="chat-ai-disclaimer">
        {uiText.composerAiDisclaimer}
      </p>
    </form>
  );
}
