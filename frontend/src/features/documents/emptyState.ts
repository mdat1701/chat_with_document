// Hàm thuần dẫn xuất trạng thái trống (T-208 §4) — không rải cờ boolean
// rải rác khắp component, một nơi duy nhất quyết định ES-01..ES-05.
import { track } from "@shared/analytics/client";
import type { DocumentStatus } from "./types";

export type EmptyStateVariant = "ES-01" | "ES-02" | "ES-03" | "ES-04" | "ES-05";

export function resolveEmptyState(
  docs: { status: DocumentStatus }[],
  hasMessages: boolean,
): EmptyStateVariant | null {
  if (docs.length === 0) return hasMessages ? "ES-05" : "ES-01";
  const ready = docs.filter((doc) => doc.status === "ready");
  if (ready.length === 0 && docs.every((doc) => doc.status === "failed")) return "ES-03";
  if (ready.length === 0) return "ES-02";
  if (!hasMessages) return "ES-04";
  return null;
}

/** Nhãn hết hạn (T-205 §5.6): số ngày còn lại tính theo lịch, âm → "hôm nay". */
export function daysUntil(dateIso: string | undefined): number | null {
  if (!dateIso) return null;
  const target = new Date(dateIso);
  if (Number.isNaN(target.getTime())) return null;
  const now = new Date();
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffMs = startOfDay(target).getTime() - startOfDay(now).getTime();
  return Math.round(diffMs / 86_400_000);
}

/** Phân nhóm kích thước tệp cho sự kiện `document_upload_started` (T-404 §3.2) — không chứa tên tệp. */
export function fileSizeBucket(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  if (mb < 1) return "lt_1mb";
  if (mb < 5) return "1_5mb";
  if (mb < 10) return "5_10mb";
  if (mb < 20) return "10_20mb";
  return "gte_20mb";
}

const SEEN_KEY_PREFIX = "cwd_empty_state_seen:";

/**
 * Phát `empty_state_viewed{state_code}` tối đa một lần mỗi variant mỗi
 * phiên trình duyệt (T-404 §3.2). Dùng `sessionStorage` làm cờ đã-xem —
 * không lưu nội dung nhạy cảm, chỉ một khóa boolean theo mã trạng thái.
 */
export function markEmptyStateViewedOnce(variant: EmptyStateVariant) {
  try {
    const key = `${SEEN_KEY_PREFIX}${variant}`;
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
    track("empty_state_viewed", { state_code: variant });
  } catch {
    // Best-effort: không chặn UI nếu sessionStorage bị khóa (chế độ riêng tư).
  }
}
