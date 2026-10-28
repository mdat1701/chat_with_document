import { create } from "zustand";
import {
  apiFetch,
  setCsrfToken,
  setUnauthorizedHandler,
} from "@shared/api/client";
import { track } from "@shared/analytics/client";
import { captureDraftOnUnauthorized } from "./draft";

export type CurrentUser = {
  id: string;
  email: string;
  display_name: string | null;
  roles: string[];
  csrf_token: string;
};

type AuthState = {
  user: CurrentUser | null;
  loading: boolean;
  load: () => Promise<void>;
};

// `session_started` (T-404 §3.2 / PRD §5.2): phát đúng một lần mỗi phiên trình
// duyệt, ngay sau khi `GET /me` trả 200 lần đầu. Dùng sessionStorage để khử
// trùng lặp giữa các lần StrictMode/remount gọi lại `load()`; bọc try/catch vì
// chế độ ẩn danh có thể chặn storage (T-106 edge case) — khi đó chấp nhận có
// thể phát lại sự kiện thay vì chặn bootstrap.
const SESSION_STARTED_FLAG = "cwd_session_started";

function markSessionStarted(): boolean {
  try {
    if (window.sessionStorage.getItem(SESSION_STARTED_FLAG)) return false;
    window.sessionStorage.setItem(SESSION_STARTED_FLAG, "1");
    return true;
  } catch {
    return true;
  }
}

/** Dùng ở `LoginScreen` để phân biệt biến thể "phiên hết hạn" khỏi lần đăng nhập đầu. */
export function hasPriorSessionInBrowser(): boolean {
  try {
    return window.sessionStorage.getItem(SESSION_STARTED_FLAG) === "1";
  } catch {
    return false;
  }
}

/**
 * `is_first_session`: codebase hiện chưa phân biệt "vừa đăng nhập qua OIDC"
 * với "tải lại trang có cookie sẵn" ở phía FE (redirect sau login do backend
 * OIDC callback xử lý — T-101). Dùng tín hiệu sẵn có gần nhất: `returnTo`/
 * query `?session=new` không tồn tại, nhưng `document.referrer` trỏ tới
 * `/auth/login` khi trình duyệt vừa được điều hướng thẳng từ bước đăng nhập
 * SSO; coi đó là phiên đầu tiên, còn lại (tải trang bình thường khi đã có
 * cookie) là phiên tiếp tục.
 */
function isFirstSession(): boolean {
  try {
    return document.referrer.includes("/auth/login");
  } catch {
    return false;
  }
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  load: async () => {
    try {
      const user = await apiFetch<CurrentUser>("/me");
      setCsrfToken(user.csrf_token);
      set({ user, loading: false });
      if (markSessionStarted()) {
        track("session_started", { is_first_session: isFirstSession() });
      }
    } catch {
      set({ user: null, loading: false });
    }
  },
}));

// Interceptor 401 toàn cục (AC-001.3): giữ bản nháp câu hỏi đang soạn rồi đặt
// lại trạng thái phiên để route guard chuyển về /login (xem shared/api/client.ts).
setUnauthorizedHandler(() => {
  captureDraftOnUnauthorized();
  useAuth.setState({ user: null, loading: false });
});
