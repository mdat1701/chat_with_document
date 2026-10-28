import "./ui.css";

export type OfflineBannerProps = {
  offline: boolean;
  message: string;
  "data-testid"?: string;
};

/**
 * Banner ngoại tuyến (T-405 §5.3, NE-03) — thuần hiển thị: cha quyết định
 * `offline` (qua `navigator.onLine` + sự kiện `online`/`offline`). Dùng
 * `position: sticky` thay vì `fixed` để không che nội dung phía dưới trong
 * khi vẫn luôn hiển thị ở đầu khung nhìn khi cuộn.
 */
export function OfflineBanner({ offline, message, "data-testid": testId }: OfflineBannerProps) {
  if (!offline) return null;
  return (
    <div role="status" aria-live="polite" className="ui-offline-banner" data-testid={testId ?? "offline-banner"}>
      <span aria-hidden="true">⚠</span>
      {message}
    </div>
  );
}
