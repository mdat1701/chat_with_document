import type { HTMLAttributes, ReactNode } from "react";
import "./ui.css";

export type BannerTone = "info" | "success" | "warning" | "danger";

export type BannerProps = Omit<HTMLAttributes<HTMLDivElement>, "role"> & {
  tone?: BannerTone;
  /** Hành động phụ, vd. nút "Thử lại" (SERVICE_BUSY — xem SDD §3.4.3). */
  actions?: ReactNode;
  "data-testid"?: string;
};

/** Thông báo trạng thái toàn trang/khu vực (offline, lỗi, cảnh báo). Thuần hiển thị. */
export function Banner({
  tone = "info",
  actions,
  children,
  className,
  "data-testid": testId,
  ...rest
}: BannerProps) {
  const isAlert = tone === "danger" || tone === "warning";
  return (
    <div
      role={isAlert ? "alert" : "status"}
      className={["ui-banner", `ui-banner--${tone}`, className]
        .filter(Boolean)
        .join(" ")}
      data-testid={testId}
      {...rest}
    >
      <div>{children}</div>
      {actions ? <div className="ui-banner__actions">{actions}</div> : null}
    </div>
  );
}
