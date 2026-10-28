import { render, screen } from "@testing-library/react";
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
