export type FileReason = "FILE_NOT_PDF" | "FILE_TOO_LARGE" | "QUOTA_EXCEEDED";
export type FileValidation = {
  file: File;
  ok: boolean;
  reasonCode?: FileReason;
};

export function validateFiles(
  files: File[],
  config: { max_file_size_bytes: number; max_documents: number },
  used: number,
): FileValidation[] {
  let accepted = 0;
  return files.map((file) => {
    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      return { file, ok: false, reasonCode: "FILE_NOT_PDF" };
    }
    if (file.size > config.max_file_size_bytes) {
      return { file, ok: false, reasonCode: "FILE_TOO_LARGE" };
    }
    if (used + accepted >= config.max_documents) {
      return { file, ok: false, reasonCode: "QUOTA_EXCEEDED" };
    }
    accepted += 1;
    return { file, ok: true };
  });
}
