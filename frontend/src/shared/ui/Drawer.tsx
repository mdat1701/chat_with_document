import type { ReactNode } from "react";
import * as RadixDialog from "@radix-ui/react-dialog";
import "./ui.css";

export type DrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  closeLabel: string;
  children?: ReactNode;
  "data-testid"?: string;
};

/**
 * Ngăn trượt dùng chung (T-405 §5.4, AC-009.3) — bọc Radix UI Dialog để có
 * sẵn bẫy focus, đóng bằng `Esc`, đóng bằng nhấn lớp phủ (scrim), và ARIA
 * đúng chuẩn, giống `Dialog` nhưng neo bên trái thay vì giữa màn hình.
 */
export function Drawer({ open, onOpenChange, title, closeLabel, children, "data-testid": testId }: DrawerProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="ui-drawer-overlay" data-testid={testId ? `${testId}-overlay` : undefined} />
        <RadixDialog.Content className="ui-drawer-content" data-testid={testId}>
          <div className="ui-drawer-header">
            <RadixDialog.Title className="ui-drawer-title">{title}</RadixDialog.Title>
            <RadixDialog.Close asChild>
              <button type="button" className="ui-icon-button" aria-label={closeLabel} data-testid={testId ? `${testId}-close` : undefined}>
                ×
              </button>
            </RadixDialog.Close>
          </div>
          {children}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
