export const messages = {
  FILE_NOT_PDF: "Chỉ hỗ trợ tệp PDF.",
  FILE_TOO_LARGE: "Tệp vượt quá 20 MB. Hãy nén hoặc tách tệp rồi tải lại.",
  QUOTA_EXCEEDED: "Đã đạt tối đa số tài liệu. Xóa bớt tài liệu để tải thêm.",
  DUPLICATE_NAME: "Tệp đã tồn tại.",
  SESSION_EXPIRED: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  NOT_AUTHORIZED: "Bạn chưa được cấp quyền sử dụng. Liên hệ quản trị viên.",
  SERVICE_BUSY: "Dịch vụ đang bận. Vui lòng thử lại.",
} as const;

export type ErrorCode = keyof typeof messages;

export function formatDate(value: string | Date) {
  return new Intl.DateTimeFormat("vi-VN").format(new Date(value));
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat("vi-VN").format(value);
}
