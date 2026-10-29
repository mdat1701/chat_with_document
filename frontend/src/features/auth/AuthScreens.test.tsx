import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { LoginScreen, NoAccessScreen } from "./AuthScreens";

vi.mock("@shared/api/client", () => ({
  logout: vi.fn(() => Promise.resolve()),
  apiFetch: vi.fn(() => Promise.reject(new Error("not used in this test"))),
  setCsrfToken: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}));

vi.mock("@shared/analytics/client", () => ({ track: vi.fn() }));

describe("AuthScreens", () => {
  afterEach(() => {
    window.sessionStorage.clear();
  });

  it("LoginScreen hiển thị tiêu đề và nút đăng nhập", () => {
    render(<LoginScreen />);
    expect(screen.getByTestId("login-sso")).toBeInTheDocument();
  });

  function withMockedLocationPathname(pathname: string) {
    const original = window.location;
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...original, pathname, assign },
    });
    return {
      assign,
      restore: () => {
        Object.defineProperty(window, "location", {
          configurable: true,
          value: original,
        });
      },
    };
  }

  it("LoginScreen gửi return_to='/' khi bấm đăng nhập từ chính route /login (AC-001.2)", () => {
    // Tái tạo đúng trường hợp phổ biến nhất: AppRoutes tự chuyển "/" sang
    // "/login" cho người dùng chưa đăng nhập TRƯỚC khi họ bấm nút — nếu
    // return_to lại là "/login", backend sẽ đưa trình duyệt quay lại đúng
    // "/login" sau khi đăng nhập xong, và vì route này render LoginScreen
    // vô điều kiện, người dùng sẽ kẹt ở màn hình đăng nhập dù đã đăng nhập
    // thành công (lỗi thật phát hiện khi chạy TC-001 qua IdP thật).
    const location = withMockedLocationPathname("/login");
    render(<LoginScreen />);
    fireEvent.click(screen.getByTestId("login-sso"));
    expect(location.assign).toHaveBeenCalledWith("/auth/login?return_to=%2F");
    location.restore();
  });

  it("LoginScreen giữ nguyên return_to khi bấm đăng nhập từ route khác /login", () => {
    const location = withMockedLocationPathname("/no-access");
    render(<LoginScreen />);
    fireEvent.click(screen.getByTestId("login-sso"));
    expect(location.assign).toHaveBeenCalledWith(
      "/auth/login?return_to=%2Fno-access",
    );
    location.restore();
  });

  it("LoginScreen không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(<LoginScreen />);
    await expectNoA11yViolations(container);
  });

  it("NoAccessScreen hiển thị tiêu đề và nút đăng xuất", () => {
    render(<NoAccessScreen />);
    expect(screen.getByText("Chưa được cấp quyền")).toBeInTheDocument();
  });

  it("NoAccessScreen không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(<NoAccessScreen />);
    await expectNoA11yViolations(container);
  });
});
