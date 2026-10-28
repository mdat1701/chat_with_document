import { useRef } from "react";
import { Button, Dialog } from "@shared/ui";
import { uiText } from "@shared/i18n/messages.vi";

type Props = {
  open: boolean;
  fileName: string;
  pending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * Hộp xác nhận xóa (T-208 §5.7, IX-04): ghi rõ tên tệp, focus mặc định ở
 * "Hủy" (không phải nút phá hủy), Esc/click ra ngoài tương đương "Hủy"
 * (Radix `onOpenChange` xử lý cả hai — AC-008.3), không đóng trước khi có
 * `204` thật (nút Xóa chỉ hiện trạng thái loading, cha quyết định khi nào
 * đóng dialog).
 */
export function DeleteConfirmDialog({
  open,
  fileName,
  pending,
  onConfirm,
  onCancel,
}: Props) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onCancel();
      }}
      title={uiText.deleteConfirmTitle}
      description={uiText.deleteConfirmDescription(fileName)}
      data-testid="delete-confirm"
      initialFocusRef={cancelRef}
      actions={
        <>
          <Button
            ref={cancelRef}
            type="button"
            variant="secondary"
            data-testid="delete-cancel"
            onClick={onCancel}
          >
            {uiText.deleteCancel}
          </Button>
          <Button
            type="button"
            variant="danger"
            data-testid="delete-submit"
            disabled={pending}
            onClick={onConfirm}
          >
            {pending ? uiText.deleteSubmitting : uiText.deleteSubmit}
          </Button>
        </>
      }
    />
  );
}
