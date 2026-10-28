import type { HTMLAttributes, ReactNode } from "react";
import "./ui.css";

export type EmptyStateProps = HTMLAttributes<HTMLDivElement> & {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  "data-testid"?: string;
};

/** Trạng thái rỗng dùng chung (vd. "Chưa có tài liệu"). Thuần hiển thị. */
export function EmptyState({ title, description, action, icon, className, "data-testid": testId, ...rest }: EmptyStateProps) {
  return (
    <div className={["ui-empty-state", className].filter(Boolean).join(" ")} data-testid={testId} {...rest}>
      {icon}
      <p className="ui-empty-state__title">{title}</p>
      {description ? <p className="ui-empty-state__description">{description}</p> : null}
      {action ? <div className="ui-empty-state__action">{action}</div> : null}
    </div>
  );
}
