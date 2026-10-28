import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoginScreen, NoAccessScreen } from "@features/auth/AuthScreens";
import { useAuth } from "@features/auth/auth";
import { UploadDropzone } from "@features/documents/UploadDropzone";
import { DocumentLibrary } from "@features/documents/DocumentLibrary";
import { ChatPage } from "@features/chat/ChatPage";
import { validateFiles } from "@shared/validation/files";

/**
 * Khung router tối thiểu (T-003, để CI build/test có gì để kiểm).
 * 4 route điều hướng theo SDD v0.3 §3.2.1 — nội dung thật của từng
 * màn hình được thay ở T-107 (auth), T-108/109/205 (tài liệu),
 * T-305-307 (hỏi đáp). Component dưới đây chỉ là placeholder.
 */
export function App() {
  const { user, loading, load } = useAuth();
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginScreen />} />
        <Route
          path="/"
          element={
            loading ? (
              <main className="page">
                <section className="card">
                  <h1 data-testid="route-placeholder">Đang tải…</h1>
                </section>
              </main>
            ) : user ? (
              <main className="page">
                <section className="card">
                  {!online && <div role="alert" className="offline-banner">Bạn đang ngoại tuyến</div>}
                  <h1 data-testid="route-placeholder">SCR-02 Thư viện tài liệu</h1>
                  <UploadDropzone disabled={!online} onFilesSelected={(files) => validateFiles(files, { max_file_size_bytes: 20 * 1024 * 1024, max_documents: 50 }, 0)} />
                  <DocumentLibrary />
                  <ChatPage />
                </section>
              </main>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
        <Route path="/no-access" element={<NoAccessScreen />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
        <Route
          path="/404"
          element={<Placeholder title="SCR-07 Không tìm thấy trang" />}
        />
      </Routes>
    </BrowserRouter>
  );
}

function Placeholder({ title }: { title: string }) {
  return <div data-testid="route-placeholder">{title}</div>;
}
