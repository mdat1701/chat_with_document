// AC-001.3 (T-107): giữ bản nháp câu hỏi khi phiên hết hạn (SDD §3.4.4).
// `sessionStorage` có thể ném lỗi ở chế độ ẩn danh — mọi truy cập bọc
// try/catch, best-effort, không bao giờ làm hỏng luồng nghiệp vụ.

export const DRAFT_STORAGE_KEY = "cwd_draft_question";

/** Lưu nội dung composer vào sessionStorage; bỏ qua nếu rỗng hoặc storage bị chặn. */
export function saveDraft(text: string): void {
  const trimmed = text.trim();
  if (!trimmed) return;
  try {
    window.sessionStorage.setItem(DRAFT_STORAGE_KEY, trimmed);
  } catch {
    // Chế độ ẩn danh có thể chặn sessionStorage — bỏ qua, không chặn điều hướng.
  }
}

/** Đọc bản nháp đã lưu, hoặc `null` nếu không có / storage bị chặn. */
export function restoreDraft(): string | null {
  try {
    return window.sessionStorage.getItem(DRAFT_STORAGE_KEY);
  } catch {
    return null;
  }
}

/** Xóa bản nháp — gọi sau khi khôi phục thành công, khi gửi câu hỏi, hoặc khi đăng xuất. */
export function clearDraft(): void {
  try {
    window.sessionStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // Không có gì để xóa nếu storage không khả dụng.
  }
}

// Sprint 1 chưa có composer thật dùng store chung (sẽ tới ở Sprint 3) — thành
// phần composer (features/chat) tự đăng ký một "nguồn đọc nội dung hiện tại"
// để interceptor 401 (shared/api/client.ts qua setUnauthorizedHandler) có thể
// lấy nội dung đang soạn mà không cần shared/api phụ thuộc ngược vào features/*.
let composerSource: (() => string) | null = null;

export function registerComposerSource(getter: (() => string) | null): void {
  composerSource = getter;
}

/** Gọi từ interceptor 401 toàn cục — lưu nháp nếu composer đang có nội dung. */
export function captureDraftOnUnauthorized(): void {
  const current = composerSource?.();
  if (current) saveDraft(current);
}
