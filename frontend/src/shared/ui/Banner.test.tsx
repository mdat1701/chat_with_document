import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Banner } from "./Banner";
import { Button } from "./Button";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Banner", () => {
  it("dùng role=alert cho cảnh báo/lỗi", () => {
    render(<Banner tone="danger" data-testid="error-banner">Có lỗi xảy ra</Banner>);
    expect(screen.getByTestId("error-banner")).toHaveAttribute("role", "alert");
  });

  it("dùng role=status cho thông tin thường", () => {
    render(<Banner tone="info" data-testid="info-banner">Đang đồng bộ</Banner>);
    expect(screen.getByTestId("info-banner")).toHaveAttribute("role", "status");
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <Banner tone="warning" actions={<Button data-testid="retry">Thử lại</Button>}>
        Dịch vụ đang bận.
      </Banner>,
    );
    await expectNoA11yViolations(container);
  });
});
