export const messages = {
  FILE_NOT_PDF: "Chỉ hỗ trợ tệp PDF.",
  FILE_TOO_LARGE: "Tệp vượt quá 20 MB. Hãy nén hoặc tách tệp rồi tải lại.",
  QUOTA_EXCEEDED: "Đã đạt tối đa số tài liệu. Xóa bớt tài liệu để tải thêm.",
  DUPLICATE_NAME: "Tệp đã tồn tại.",
  SESSION_EXPIRED: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  NOT_AUTHORIZED: "Bạn chưa được cấp quyền sử dụng. Liên hệ quản trị viên.",
  SERVICE_BUSY: "Dịch vụ đang bận. Vui lòng thử lại.",
  UPLOAD_NETWORK: "Mất kết nối. Hãy thử lại.",
  UPLOAD_ABORTED: "Đã hủy tải lên.",
  RATE_LIMITED: "Quá nhiều yêu cầu. Vui lòng thử lại sau ít phút.",
  DOC_NOT_FOUND: "Không tìm thấy tài liệu. Tài liệu có thể đã bị xóa.",
  RETRY_NOT_ALLOWED: "Không thể thử lại tài liệu này.",
  INGESTION_FAILED: "Xử lý tài liệu thất bại.",
  PDF_NO_TEXT: "Tệp PDF không có văn bản để xử lý.",
  // T-307 §3 — danh mục lỗi khi trả lời câu hỏi (SDD §3.4.3). Không hiển thị
  // mã HTTP hay thông báo nguyên văn của máy chủ cho người dùng.
  ANSWER_NETWORK: "Mất kết nối. Câu hỏi chưa được trả lời.",
  ANSWER_TIMEOUT: "Hệ thống phản hồi quá lâu. Vui lòng thử lại.",
  ANSWER_INTERRUPTED: "Câu trả lời chưa hoàn chỉnh do bị gián đoạn.",
  QUESTION_INVALID: "Câu hỏi không hợp lệ. Vui lòng kiểm tra lại nội dung.",
  NO_READY_DOCUMENTS: "Không có tài liệu nào sẵn sàng để trả lời.",
} as const;

export type ErrorCode = keyof typeof messages;

/** Chuỗi không gắn với mã lỗi — dùng cho EmptyState, dialog, toast, bộ đếm. */
export const uiText = {
  documentCounter: (used: number, max: number) =>
    `${formatNumber(used)}/${formatNumber(max)} tài liệu`,
  quotaReached: "Đã đạt tối đa 50 tài liệu. Xóa bớt tài liệu để tải thêm.",
  statusUploading: (percent: number) => `Đang tải lên ${percent}%`,
  statusProcessing: "Đang xử lý…",
  statusReady: "Sẵn sàng",
  statusFailed: "Lỗi",
  expiringToday: "Sẽ bị xóa hôm nay",
  expiringInDays: (days: number) => `Sẽ bị xóa sau ${days} ngày`,
  deleteConfirmTitle: "Xóa tài liệu?",
  deleteConfirmDescription: (name: string) =>
    `Bạn sắp xóa "${name}". Thao tác này không thể hoàn tác.`,
  deleteCancel: "Hủy",
  deleteSubmit: "Xóa",
  deleteSubmitting: "Đang xóa…",
  deletedToast: (name: string) => `Đã xóa "${name}".`,
  duplicateTitle: "Tệp đã tồn tại",
  duplicateDescription: (name: string) =>
    `"${name}" đã có trong thư viện của bạn.`,
  duplicateReplace: "Thay thế tệp cũ",
  duplicateKeepBoth: "Giữ cả hai",
  duplicateCancel: "Hủy",
  rejectedFilesTitle: "Một số tệp không được tải lên",
  retry: "Thử lại",
  cancelUpload: "Hủy",
  es01Title: "Chưa có tài liệu nào",
  es01Description: "① Tải PDF lên ② Chờ trạng thái ✅ ③ Đặt câu hỏi",
  es01Action: "Tải tài liệu lên",
  es02Title: "Tài liệu đang được xử lý, vui lòng chờ…",
  es02Description: "Ô câu hỏi sẽ mở khi có ít nhất một tài liệu sẵn sàng.",
  es03Title: "Không có tài liệu nào sẵn sàng",
  es03Description: "Kiểm tra lỗi ở danh sách bên trái và thử tải lại.",
  es04Title: "Bạn có thể hỏi, ví dụ:",
  es05Title: "Chưa có tài liệu nào",
  es05Description:
    "Tải lại tài liệu để tiếp tục hỏi đáp. Hội thoại cũ vẫn được giữ nguyên bên phải.",
  composerLockedNoReady: "Tải tài liệu lên để bắt đầu hỏi",
  composerLockedProcessing: "Tài liệu đang được xử lý, vui lòng chờ…",
  composerLockedAllFailed: "Không có tài liệu nào sẵn sàng",
  // T-305 — composer (SDD §3.7.3, 7 trạng thái theo thứ tự ưu tiên).
  composerLockedOffline: "Bạn đang ngoại tuyến",
  composerLockedAwaitingAnswer: "Đang trả lời câu hỏi trước…",
  composerPlaceholder: "Nhập câu hỏi…",
  composerLabel: "Câu hỏi của bạn",
  composerSubmit: "Gửi",
  composerCharCounter: (len: number, max: number) =>
    `${formatNumber(len)}/${formatNumber(max)}`,
  composerAiDisclaimer:
    "Câu trả lời do AI tạo — hãy kiểm tra nguồn trước khi sử dụng",
  composerExamplesTitle: "Bạn có thể hỏi, ví dụ:",
  composerExamples: [
    "Hợp đồng này có hiệu lực đến khi nào?",
    "Điều khoản thanh toán được quy định ở đâu?",
    "Tóm tắt nội dung chính của tài liệu này.",
  ],
  // T-306/T-307 — vòng đời câu trả lời (SDD §3.7.2).
  typingIndicator: (n: number) => `Đang tìm trong ${formatNumber(n)} tài liệu…`,
  answerPending: "Đặt câu hỏi để bắt đầu.",
  answerLatency: (seconds: number) =>
    `Trả lời trong ${seconds.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} giây`,
  answerUncitedWarning: "Không xác định được nguồn — vui lòng kiểm chứng",
  answerPartialNote:
    "Một phần thông tin không tìm thấy trong tài liệu đã tải lên.",
  answerIncompleteNote: "Câu trả lời chưa hoàn chỉnh.",
  answeredLiveRegion: "Đã có câu trả lời",
  notFoundTitle: "Không tìm thấy thông tin này trong các tài liệu đã tải lên.",
  notFoundHint: "Thử diễn đạt lại câu hỏi hoặc tải thêm tài liệu.",
  retryLabel: "Thử lại",
  resendLabel: "Gửi lại",
  citationPagePrefix: "tr.",
  citationLabel: (index: number, name: string) => `Nguồn ${index}: ${name}`,
  // T-405 — banner ngoại tuyến, ngăn trượt tài liệu, menu người dùng.
  offlineBannerMessage: "Bạn đang ngoại tuyến",
  uploadLockedOffline: "Bạn đang ngoại tuyến. Kết nối lại để tải tài liệu.",
  openDocumentDrawer: "Tài liệu",
  closeDocumentDrawer: "Đóng",
  documentDrawerTitle: "Tài liệu của bạn",
  userMenuHelp: "Trợ giúp",
  userMenuLogout: "Đăng xuất",
  // T-405 §5 bước 6 — phím tắt Ctrl+Shift+O (cuộc trò chuyện mới).
  newConversationToast: "Đã bắt đầu cuộc trò chuyện mới",
} as const;

// Chuỗi hiển thị cố định của features/auth (SCR-01, SCR-03 — T-107).
// Tách khỏi `messages` ở trên vì đây không phải mã lỗi SDD §3.4.3 (giữ
// `ErrorCode` chỉ gồm các mã lỗi thật) nhưng vẫn theo cùng quy ước đặt tên.
export const authMessages = {
  LOGIN_TITLE: "Chat với tài liệu",
  LOGIN_SUBTITLE: "Đăng nhập bằng tài khoản công ty để bắt đầu.",
  LOGIN_CTA: "Đăng nhập",
  LOGIN_DRAFT_KEPT: "Câu hỏi bạn đang soạn đã được giữ lại.",
  NO_ACCESS_TITLE: "Chưa được cấp quyền",
  NO_ACCESS_BODY: "Tài khoản của bạn chưa được bật quyền truy cập.",
  NO_ACCESS_LOGOUT_CTA: "Đăng nhập bằng tài khoản khác",
} as const;

export function formatDate(value: string | Date) {
  return new Intl.DateTimeFormat("vi-VN").format(new Date(value));
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat("vi-VN").format(value);
}
