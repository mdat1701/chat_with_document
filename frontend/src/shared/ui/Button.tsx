import { forwardRef, type ButtonHTMLAttributes } from "react";
import "./ui.css";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  "data-testid"?: string;
};

/** Nút bấm dùng chung (SDD §3.2.3). Thuần hiển thị — không gọi API. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      className,
      type = "button",
      "data-testid": testId,
      ...rest
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        className={["ui-button", `ui-button--${variant}`, className]
          .filter(Boolean)
          .join(" ")}
        data-testid={testId}
        {...rest}
      />
    );
  },
);
