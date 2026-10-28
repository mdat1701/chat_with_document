import { Badge, type BadgeTone } from "@shared/ui";
import { messages, type ErrorCode, uiText } from "@shared/i18n/messages.vi";
import { daysUntil } from "./emptyState";
import type { DocumentStatus } from "./types";

type Props = {
  status: DocumentStatus;
  errorCode?: string | null;
  progress?: number;
  expiresAt?: string;
};

function errorMessage(code?: string | null): string {
  if (code && code in messages) return messages[code as ErrorCode];
  return messages.SERVICE_BUSY;
}

/**
 * Trạng thái tài liệu luôn kèm icon + chữ, không chỉ màu (IX-07/WCAG AA —
 * T-205 §2 AC-010.3). `aria-label` đọc đầy đủ cả trạng thái lẫn lý do lỗi.
 */
export function StatusBadge({ status, errorCode, progress, expiresAt }: Props) {
  if (status === "uploading") {
    const text = uiText.statusUploading(progress ?? 0);
    return (
      <Badge tone="info" data-testid="doc-status" aria-label={text}>
        ⏳ {text}
      </Badge>
    );
  }
  if (status === "failed") {
    const text = `${uiText.statusFailed} — ${errorMessage(errorCode)}`;
    return (
      <Badge
        tone="danger"
        data-testid="doc-status"
        aria-label={text}
        title={errorMessage(errorCode)}
      >
        ❌ {uiText.statusFailed}
      </Badge>
    );
  }
  if (status === "ready") {
    const days = daysUntil(expiresAt);
    if (days !== null && days <= 7) {
      const text =
        days <= 0 ? uiText.expiringToday : uiText.expiringInDays(days);
      return (
        <Badge tone="warning" data-testid="doc-status" aria-label={text}>
          ⚠ {text}
        </Badge>
      );
    }
    return (
      <Badge
        tone="success"
        data-testid="doc-status"
        aria-label={uiText.statusReady}
      >
        ✅ {uiText.statusReady}
      </Badge>
    );
  }
  const tone: BadgeTone = "info";
  return (
    <Badge
      tone={tone}
      data-testid="doc-status"
      aria-label={uiText.statusProcessing}
    >
      ⏳ {uiText.statusProcessing}
    </Badge>
  );
}
