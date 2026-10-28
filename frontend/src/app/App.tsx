import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

/**
 * Khung router tối thiểu (T-003, để CI build/test có gì để kiểm).
 * 4 route điều hướng theo SDD v0.3 §3.2.1 — nội dung thật của từng
 * màn hình được thay ở T-107 (auth), T-108/109/205 (tài liệu),
 * T-305-307 (hỏi đáp). Component dưới đây chỉ là placeholder.
 */
export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={<Placeholder title="SCR-01 Đăng nhập" />}
        />
        <Route
          path="/"
          element={<Placeholder title="SCR-02 Màn hình chính" />}
        />
        <Route
          path="/no-access"
          element={<Placeholder title="SCR-03 Chưa được cấp quyền" />}
        />
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
