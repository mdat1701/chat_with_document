import type { HTMLAttributes } from "react";
import "./ui.css";

export type SkeletonProps = HTMLAttributes<HTMLDivElement> & {
  width?: string | number;
  height?: string | number;
  "data-testid"?: string;
};

/** Khối giữ chỗ khi đang tải dữ liệu. Thuần hiển thị, không gọi API. */
export function Skeleton({ width = "100%", height = "1rem", style, className, "data-testid": testId, ...rest }: SkeletonProps) {
  return (
    <div
      role="presentation"
      aria-hidden="true"
      className={["ui-skeleton", className].filter(Boolean).join(" ")}
      style={{ width, height, ...style }}
      data-testid={testId}
      {...rest}
    />
  );
}
