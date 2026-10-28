import { useEffect, useState } from "react";

/**
 * T-405 §5.4 (AC-009.3) — điểm ngắt `lg` = 1024px (SDD §3.8.1). `true` từ
 * 1024px trở lên dùng bố cục 2 cột; dưới ngưỡng này thư viện tài liệu
 * chuyển sang ngăn trượt. Dùng `matchMedia` (không phải `window.innerWidth`
 * đọc một lần) để tự cập nhật khi xoay màn hình/đổi kích thước cửa sổ.
 */
export function useIsDesktop(): boolean {
  const query = "(min-width: 1024px)";
  const [isDesktop, setIsDesktop] = useState(() => {
    try {
      return window.matchMedia(query).matches;
    } catch {
      return true;
    }
  });

  useEffect(() => {
    let mql: MediaQueryList;
    try {
      mql = window.matchMedia(query);
    } catch {
      return;
    }
    const handler = (event: MediaQueryListEvent) => setIsDesktop(event.matches);
    mql.addEventListener("change", handler);
    setIsDesktop(mql.matches);
    return () => mql.removeEventListener("change", handler);
  }, []);

  return isDesktop;
}
