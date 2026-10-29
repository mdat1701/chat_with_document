import { logout } from "@shared/api/client";
import { messages, authMessages } from "@shared/i18n/messages.vi";
import { Banner, Button } from "@shared/ui";
import { clearDraft, restoreDraft } from "./draft";
import { hasPriorSessionInBrowser } from "./auth";

export function LoginScreen() {
  // Biến thể "phiên hết hạn" (SCR-01): chỉ hiện banner khi trình duyệt đã từng
  // có phiên hợp lệ trước đó trong tab này (đăng nhập lần đầu không hiện).
  const sessionExpired = hasPriorSessionInBrowser();
  const hasDraft = restoreDraft() !== null;
  return (
    <main className="page">
      <section className="card" aria-labelledby="login-title">
        <h1 id="login-title">{authMessages.LOGIN_TITLE}</h1>
        {sessionExpired && (
          <Banner tone="warning" data-testid="session-expired-banner">
            {messages.SESSION_EXPIRED}
            {hasDraft ? ` ${authMessages.LOGIN_DRAFT_KEPT}` : null}
          </Banner>
        )}
        <p>{authMessages.LOGIN_SUBTITLE}</p>
        <Button
          data-testid="login-sso"
          onClick={() => {
            // AC-001.2: `/login` luôn render LoginScreen bất kể trạng thái
            // đăng nhập (App.tsx không gate route này) — nếu return_to lại
            // chính là "/login" (trường hợp PHỔ BIẾN NHẤT: người dùng chưa
            // đăng nhập mở "/" bị AppRoutes tự chuyển sang "/login" TRƯỚC
            // khi họ bấm nút), backend sẽ đưa trình duyệt quay lại đúng
            // "/login" sau khi tạo phiên thành công — người dùng kẹt ở màn
            // hình đăng nhập dù đã đăng nhập xong (phát hiện khi chạy thật
            // TC-001 qua IdP, không phải chỉ đọc code). "/" là đích hợp lệ
            // duy nhất hiện có (chưa có deep-link khác trong SPA).
            const pathname = window.location.pathname;
            const returnTo = pathname === "/login" ? "/" : pathname;
            window.location.assign(
              `/auth/login?return_to=${encodeURIComponent(returnTo)}`,
            );
          }}
        >
          {authMessages.LOGIN_CTA}
        </Button>
      </section>
    </main>
  );
}

export function NoAccessScreen() {
  return (
    <main className="page">
      <section className="card" aria-labelledby="access-title">
        <h1 id="access-title">{authMessages.NO_ACCESS_TITLE}</h1>
        <p>{authMessages.NO_ACCESS_BODY}</p>
        <Button
          variant="secondary"
          onClick={() => {
            clearDraft();
            void logout().finally(() => {
              window.location.href = "/login";
            });
          }}
        >
          {authMessages.NO_ACCESS_LOGOUT_CTA}
        </Button>
      </section>
    </main>
  );
}
