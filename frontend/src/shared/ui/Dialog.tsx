import type { ReactNode, RefObject } from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import "./ui.css";

export type DialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children?: ReactNode;
  /** Hành động (nút Xác nhận/Hủy) hiển thị ở cuối hộp thoại. */
  actions?: ReactNode;
  /**
   * Phần tử nhận focus khi hộp thoại mở, thay cho mặc định của Radix
   * (nội dung hộp thoại). Dùng cho IX-04: hộp xác nhận xóa đặt focus mặc
   * định ở nút "Hủy", không phải nút phá hủy.
   */
  initialFocusRef?: RefObject<HTMLElement>;
  "data-testid"?: string;
};

/**
 * Hộp thoại dùng chung, bọc Radix UI (`@radix-ui/react-dialog`) để có sẵn
 * focus trap, đóng bằng Esc, và ARIA đúng chuẩn (CN-08). Thuần hiển thị.
 */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  actions,
  initialFocusRef,
  "data-testid": testId,
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="ui-dialog-overlay" />
        <RadixDialog.Content
          className="ui-dialog-content"
          data-testid={testId}
          onOpenAutoFocus={(event) => {
            if (initialFocusRef?.current) {
              event.preventDefault();
              initialFocusRef.current.focus();
            }
          }}
        >
          <RadixDialog.Title className="ui-dialog-title">
            {title}
          </RadixDialog.Title>
          {description ? (
            <RadixDialog.Description className="ui-dialog-description">
              {description}
            </RadixDialog.Description>
          ) : null}
          {children}
          {actions ? <div className="ui-dialog-actions">{actions}</div> : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}

export const DialogClose = RadixDialog.Close;
