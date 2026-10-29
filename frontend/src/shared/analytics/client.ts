type AnalyticsEvent = {
  event_name: string;
  timestamp: string;
  props: Record<string, unknown>;
};

const queue: AnalyticsEvent[] = [];

export function track(event_name: string, props: Record<string, unknown> = {}) {
  queue.push({ event_name, timestamp: new Date().toISOString(), props });
  if (queue.length >= 20) void flush();
}

// T-404 §5 bước 5: "gom lô theo thời gian (ví dụ 5 giây) HOẶC khi đủ 20
// sự kiện" — bản trước chỉ cài nhánh đếm 20, thiếu hẳn nhánh theo thời
// gian. Hậu quả thật: một phiên bình thường hiếm khi đạt 20 sự kiện
// trước khi người dùng rời trang theo cách không chắc chắn kích hoạt
// `pagehide` (ví dụ chuyển hẳn sang ứng dụng khác, đóng máy đột ngột,
// một số trình duyệt mobile không bắn `pagehide` đáng tin cậy) — toàn
// bộ phễu kích hoạt/MET-003 mà T-404 tồn tại để đo gần như không bao
// giờ nhận được dữ liệu trong phiên dùng bình thường. Phát hiện khi
// chạy TC-020 thủ công: thao tác đủ để tạo nhiều sự kiện hợp lệ
// (`document_upload_started`, `question_submitted`, ...) nhưng không
// sự kiện nào tới được `/api/v1/events` vì không đủ 20 và trang không
// đóng.
const FLUSH_INTERVAL_MS = 5000;
setInterval(() => void flush(), FLUSH_INTERVAL_MS);

export async function flush() {
  if (!queue.length) return;
  const events = queue.splice(0, queue.length);
  try {
    await fetch("/api/v1/events", {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ events }),
      keepalive: true,
    });
  } catch {
    // Analytics is best-effort and must not interrupt product flows.
  }
}

window.addEventListener("pagehide", () => {
  if (!queue.length) return;
  navigator.sendBeacon(
    "/api/v1/events",
    JSON.stringify({ events: queue.splice(0, queue.length) }),
  );
});
