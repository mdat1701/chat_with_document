import { useCallback, useEffect, useState } from "react";
import {
  apiFetch,
  subscribeDocumentEvents,
  type DocumentEventPayload,
} from "@shared/api/client";
import type { DocumentStatus, DocumentVM } from "./types";

type RawDocument = {
  id: string;
  name: string;
  size_bytes: number;
  page_count: number | null;
  status: string;
  error_code: string | null;
  uploaded_at?: string;
  expires_at?: string;
};

function toVM(raw: RawDocument): DocumentVM {
  return {
    id: raw.id,
    name: raw.name,
    sizeBytes: raw.size_bytes,
    pageCount: raw.page_count,
    status: raw.status as DocumentStatus,
    errorCode: raw.error_code,
    uploadedAt: raw.uploaded_at,
    expiresAt: raw.expires_at,
  };
}

/**
 * Tải `GET /documents` và hợp nhất sự kiện SSE `GET /documents/events`
 * (T-205 §5.1-§5.2). Không dùng TanStack Query (chưa có `QueryClientProvider`
 * nào được dựng ở `App.tsx` trong phiên này — xem ghi chú T-205) — state
 * nằm trong RAM qua `useState`, không ghi `localStorage` (CN-06).
 */
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentVM[]>([]);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    try {
      const rows = await apiFetch<RawDocument[]>("/documents");
      setDocuments(rows.map(toVM));
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    const unsubscribe = subscribeDocumentEvents(
      (payload: DocumentEventPayload) => {
        setDocuments((current) => {
          const index = current.findIndex((item) => item.id === payload.id);
          if (index === -1) {
            // Tài liệu chưa có trong cache cục bộ (vd. tải từ tab khác) — làm mới toàn bộ.
            void reload();
            return current;
          }
          const next = [...current];
          next[index] = {
            ...next[index],
            status: payload.status as DocumentStatus,
            errorCode: payload.error_code,
            pageCount: payload.page_count ?? next[index].pageCount,
          };
          return next;
        });
      },
      () => {
        // T-204 §5 bước 5: khi mất kết nối SSE (EventSource tự reconnect),
        // đồng bộ lại bằng GET /documents — nguồn sự thật là DB, không
        // phải luồng sự kiện có thể bị lỡ trong lúc mất kết nối.
        void reload();
      },
    );
    return unsubscribe;
  }, [reload]);

  /** Chèn lạc quan một tài liệu vừa nhận `201` từ hàng đợi tải lên cục bộ. */
  const upsertFromUpload = useCallback(
    (doc: { id: string; name: string; status: string }) => {
      setDocuments((current) => {
        if (current.some((item) => item.id === doc.id)) return current;
        return [
          {
            id: doc.id,
            name: doc.name,
            sizeBytes: 0,
            pageCount: null,
            status: doc.status as DocumentStatus,
          },
          ...current,
        ];
      });
    },
    [],
  );

  const removeLocal = useCallback((id: string) => {
    setDocuments((current) => current.filter((item) => item.id !== id));
  }, []);

  return { documents, loading, reload, upsertFromUpload, removeLocal };
}
