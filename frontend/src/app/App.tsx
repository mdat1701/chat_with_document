import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { LoginScreen, NoAccessScreen } from "@features/auth/AuthScreens";
import { useAuth } from "@features/auth/auth";
import { DocumentLibrary } from "@features/documents/DocumentLibrary";
import { ChatPage } from "@features/chat/ChatPage";
import { AppConfigProvider } from "@shared/config";
import { Drawer, OfflineBanner, ToastProvider, ToastRegion } from "@shared/ui";
import { uiText } from "@shared/i18n/messages.vi";
import { UserMenu } from "./UserMenu";
import { useIsDesktop } from "./useIsDesktop";

/**
 * Khung router tối thiểu (T-003, để CI build/test có gì để kiểm).
 * 4 route điều hướng theo SDD v0.3 §3.2.1 — nội dung thật của từng
 * màn hình được thay ở T-107 (auth), T-108/109/205 (tài liệu),
 * T-305-307 (hỏi đáp). Component dưới đây chỉ là placeholder.
 */
export function App() {
  return (
    <AppConfigProvider>
      <ToastProvider>
        <AppRoutes />
        <ToastRegion data-testid="toast-region" />
      </ToastProvider>
    </AppConfigProvider>
  );
}

function AppRoutes() {
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
              <MainScreen online={online} />
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

/**
 * SCR-02 (T-405 §5.4) — header + bố cục 2 cột ở `lg` (1024px) trở lên; dưới
 * ngưỡng đó thư viện tài liệu chuyển sang ngăn trượt mở bằng nút "Tài liệu".
 */
function MainScreen({ online }: { online: boolean }) {
  const isDesktop = useIsDesktop();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Mở ngăn rồi xoay ngang lên >=1024px: chuyển hẳn sang bố cục 2 cột nên
  // nhánh ngăn trượt (và `drawerOpen`) không còn render — không kẹt "đang mở".
  useEffect(() => {
    if (isDesktop) setDrawerOpen(false);
  }, [isDesktop]);

  return (
    <div className="app-shell">
      <OfflineBanner offline={!online} message={uiText.offlineBannerMessage} />
      <header className="app-header">
        <h1 className="app-header__title" data-testid="route-placeholder">
          SCR-02 Thư viện tài liệu
        </h1>
        <div className="app-header__actions">
          {!isDesktop && (
            <button
              type="button"
              className="ui-button ui-button--secondary"
              data-testid="open-document-drawer"
              onClick={() => setDrawerOpen(true)}
            >
              {uiText.openDocumentDrawer}
            </button>
          )}
          <UserMenu />
        </div>
      </header>
      <main className="app-main">
        {isDesktop ? (
          <div className="app-layout app-layout--two-col">
            <DocumentLibrary online={online} />
            <ChatPage />
          </div>
        ) : (
          <div className="app-layout">
            <ChatPage />
            <Drawer
              open={drawerOpen}
              onOpenChange={setDrawerOpen}
              title={uiText.documentDrawerTitle}
              closeLabel={uiText.closeDocumentDrawer}
              data-testid="document-drawer"
            >
              <DocumentLibrary online={online} />
            </Drawer>
          </div>
        )}
      </main>
    </div>
  );
}

function Placeholder({ title }: { title: string }) {
  return <div data-testid="route-placeholder">{title}</div>;
}
