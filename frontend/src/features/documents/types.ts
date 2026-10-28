// Kiểu dữ liệu dùng chung cho features/documents (T-109/T-205/T-208).
export type DocumentStatus = "uploading" | "processing" | "ready" | "failed";

export type DocumentVM = {
  id: string;
  name: string;
  sizeBytes: number;
  pageCount: number | null;
  status: DocumentStatus;
  uploadProgress?: number;
  errorCode?: string | null;
  uploadedAt?: string;
  expiresAt?: string;
};
