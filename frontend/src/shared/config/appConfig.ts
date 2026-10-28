// Hợp đồng dữ liệu của GET /api/v1/config (backend/app/api/routers/config.py).
export type AppConfig = {
  max_file_size_bytes: number;
  max_documents: number;
  max_pages: number;
  retention_days: number;
  max_question_length: number;
  answer_timeout_ms: number;
  features: { citation_page_numbers: boolean };
  retrieval: { tau: number; top_k: number; max_chunks_per_doc: number };
  supported_languages: string[];
};

// Giá trị mặc định an toàn khi GET /config lỗi lúc khởi động (SDD §3.4.4,
// mục "Trường hợp biên" của T-106): 20 MB / 50 tài liệu / 2.000 ký tự.
export const DEFAULT_APP_CONFIG: AppConfig = {
  max_file_size_bytes: 20 * 1024 * 1024,
  max_documents: 50,
  max_pages: 200,
  retention_days: 30,
  max_question_length: 2000,
  answer_timeout_ms: 30000,
  features: { citation_page_numbers: true },
  retrieval: { tau: 0.5, top_k: 5, max_chunks_per_doc: 3 },
  supported_languages: ["vi"],
};
