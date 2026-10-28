import { Button, Dialog } from "@shared/ui";
import { uiText } from "@shared/i18n/messages.vi";

type Props = {
  fileName: string;
  onReplace: () => void;
  onKeepBoth: () => void;
  onCancel: () => void;
};

/**
 * Tệp trùng tên (ER-08, T-109 §4): mở tuần tự — hàng đợi xử lý tối đa một
 * hộp thoại tại một thời điểm (xem `useUploadQueue.resolveDuplicate`).
 */
export function DuplicateFileDialog({
  fileName,
  onReplace,
  onKeepBoth,
  onCancel,
}: Props) {
  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next) onCancel();
      }}
      title={uiText.duplicateTitle}
      description={uiText.duplicateDescription(fileName)}
      data-testid="duplicate-file-dialog"
      actions={
        <>
          <Button
            type="button"
            variant="secondary"
            data-testid="duplicate-cancel"
            onClick={onCancel}
          >
            {uiText.duplicateCancel}
          </Button>
          <Button
            type="button"
            variant="secondary"
            data-testid="duplicate-keep-both"
            onClick={onKeepBoth}
          >
            {uiText.duplicateKeepBoth}
          </Button>
          <Button
            type="button"
            variant="primary"
            data-testid="duplicate-replace"
            onClick={onReplace}
          >
            {uiText.duplicateReplace}
          </Button>
        </>
      }
    />
  );
}
