import type { HTMLAttributes } from "react";
import "./ui.css";

export type BadgeTone = "neutral" | "success" | "warning" | "danger" | "info";

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  tone?: BadgeTone;
  "data-testid"?: string;
};

/** Nhãn trạng thái nhỏ (vd. trạng thái xử lý tài liệu). Thuần hiển thị. */
export function Badge({ tone = "neutral", className, "data-testid": testId, ...rest }: BadgeProps) {
  return (
    <span
      className={["ui-badge", `ui-badge--${tone}`, className].filter(Boolean).join(" ")}
      data-testid={testId}
      {...rest}
    />
  );
}
