import { useRef, type DragEvent, type KeyboardEvent } from "react";
import { uploadFile } from "@shared/api/client";

type Props = {
  disabled?: boolean;
  onFilesSelected: (files: File[]) => void;
};

export function UploadDropzone({ disabled = false, onFilesSelected }: Props) {
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
      const files = Array.from(event.dataTransfer.files);
      onFilesSelected(files);
      void Promise.all(files.map((file) => uploadFile(file)));
    }
  };
  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
      aria-label="Chọn tệp PDF để tải lên"
      data-testid="upload-dropzone"
      onClick={choose}
      onKeyDown={keyDown}
      onDragOver={(event) => event.preventDefault()}
      onDrop={drop}
      style={{ border: "2px dashed #b8c5d9", borderRadius: 12, padding: 28 }}
    >
      <strong>Tải tài liệu PDF</strong>
      <p>PDF có văn bản · tối đa 20 MB mỗi tệp</p>
      <input
        ref={inputRef}
        hidden
        type="file"
        multiple
        data-testid="upload-dropzone-input"
        accept="application/pdf,.pdf"
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          onFilesSelected(files);
          void Promise.all(files.map((file) => uploadFile(file)));
          event.target.value = "";
        }}
      />
    </div>
  );
}
