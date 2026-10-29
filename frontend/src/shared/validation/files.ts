export type FileReason = "FILE_NOT_PDF" | "FILE_TOO_LARGE" | "QUOTA_EXCEEDED";
export type FileValidation = {
  file: File;
  ok: boolean;
  reasonCode?: FileReason;
};

const PDF_MAGIC_BYTES = "%PDF-";

// Đọc 5 byte đầu tệp và so với chữ ký PDF thật ("%PDF-"), thay vì chỉ tin
// `file.type`/đuôi tệp (dễ giả: đổi tên "ảnh.png" thành "ảnh.pdf"). Trả về
// `true` khi không đọc được (ví dụ môi trường không có FileReader) để không
// chặn nhầm — server vẫn kiểm tra lại bằng 415 nếu client bỏ sót.
function hasPdfSignature(file: File): Promise<boolean> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const head = reader.result;
      if (!(head instanceof ArrayBuffer)) {
        resolve(true);
        return;
      }
      const signature = new TextDecoder("ascii").decode(head);
      resolve(signature === PDF_MAGIC_BYTES);
    };
    reader.onerror = () => resolve(true);
    reader.readAsArrayBuffer(file.slice(0, PDF_MAGIC_BYTES.length));
  });
}

export async function validateFiles(
  files: File[],
  config: { max_file_size_bytes: number; max_documents: number },
  used: number,
): Promise<FileValidation[]> {
  let accepted = 0;
  const results: FileValidation[] = [];
  for (const file of files) {
    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      results.push({ file, ok: false, reasonCode: "FILE_NOT_PDF" });
      continue;
    }
    if (!(await hasPdfSignature(file))) {
      results.push({ file, ok: false, reasonCode: "FILE_NOT_PDF" });
      continue;
    }
    if (file.size > config.max_file_size_bytes) {
      results.push({ file, ok: false, reasonCode: "FILE_TOO_LARGE" });
      continue;
    }
    if (used + accepted >= config.max_documents) {
      results.push({ file, ok: false, reasonCode: "QUOTA_EXCEEDED" });
      continue;
    }
    accepted += 1;
    results.push({ file, ok: true });
  }
  return results;
}
