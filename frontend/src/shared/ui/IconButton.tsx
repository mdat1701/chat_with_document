import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
import "./ui.css";

export type IconButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  /** Nhãn ẩn phục vụ trình đọc màn hình — bắt buộc vì nút chỉ có icon. */
  label: string;
  icon: ReactNode;
  "data-testid"?: string;
};

/** Nút chỉ chứa icon, luôn có `aria-label` để đạt WCAG 2.1 AA. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { label, icon, className, type = "button", "data-testid": testId, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      title={label}
      className={["ui-icon-button", className].filter(Boolean).join(" ")}
      data-testid={testId}
      {...rest}
    >
      {icon}
    </button>
  );
});
