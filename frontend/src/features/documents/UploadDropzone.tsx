import { useRef, type DragEvent, type KeyboardEvent } from "react";
import { Tooltip } from "@shared/ui";

type Props = {
  disabled?: boolean;
  /** Lý do vô hiệu hóa — bắt buộc có khi `disabled` (SDD §2.5: nút disabled luôn có tooltip). */
  disabledReason?: string;
  hintText: string;
  onFilesSelected: (files: File[]) => void;
};

/**
 * Vùng kéo-thả/chọn tệp (T-109 §5.1) — thuần phía UI: chỉ gom danh sách
 * `File` và giao lại cho `onFilesSelected` (hàng đợi tải lên thật nằm ở
 * `useUploadQueue`, gọi từ `DocumentLibrary`). Không tự gọi API, nên không
 * vi phạm ranh giới DR-04.
 */
export function UploadDropzone({
  disabled = false,
  disabledReason,
  hintText,
  onFilesSelected,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const choose = () => {
    if (!disabled) inputRef.current?.click();
  };
  const keyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose();
    }
  };
  const drop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (!disabled) {
      onFilesSelected(Array.from(event.dataTransfer.files));
    }
  };

  const dropzone = (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label="Chọn tệp PDF để tải lên"
      data-testid="upload-dropzone"
      className="ui-upload-dropzone"
      onClick={choose}
      onKeyDown={keyDown}
      onDragOver={(event) => event.preventDefault()}
      onDrop={drop}
    >
      <strong>Tải tài liệu PDF</strong>
      <p>{hintText}</p>
      <input
        ref={inputRef}
        hidden
        type="file"
        multiple
        data-testid="upload-dropzone-input"
        accept="application/pdf,.pdf"
        disabled={disabled}
        onChange={(event) => {
          onFilesSelected(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />
    </div>
  );

  if (disabled && disabledReason) {
    return (
      <Tooltip content={disabledReason} data-testid="upload-dropzone-tooltip">
        {dropzone}
      </Tooltip>
    );
  }
  return dropzone;
}
