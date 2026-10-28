import { useEffect, useState } from "react";
import { apiFetch } from "@shared/api/client";

type DocumentItem = {
  id: string;
  name: string;
  size_bytes: number;
  status: string;
  page_count: number | null;
  error_code: string | null;
};

export function DocumentLibrary() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const load = () => apiFetch<DocumentItem[]>("/documents").then(setDocuments).catch(() => setDocuments([]));
  useEffect(() => { void load(); }, []);
  const remove = async (id: string) => {
    if (!window.confirm("Xóa tài liệu này?")) return;
    await apiFetch<void>(`/documents/${id}`, { method: "DELETE" });
    await load();
  };
  return (
    <section aria-label="Thư viện tài liệu">
      <h2>Tài liệu của bạn</h2>
      {documents.length === 0 ? <p data-testid="empty-state">Chưa có tài liệu. Hãy tải PDF đầu tiên.</p> : (
        <ul className="document-list">
          {documents.map((doc) => (
            <li key={doc.id} className="document-row" data-testid="doc-item">
              <span><strong>{doc.name}</strong><small>{doc.status}{doc.page_count ? ` · ${doc.page_count} trang` : ""}</small></span>
              <button type="button" data-testid="doc-delete" onClick={() => void remove(doc.id)}>Xóa</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
