import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "./Badge";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Badge", () => {
  it("hiển thị nội dung và data-testid", () => {
    render(<Badge tone="success" data-testid="status-badge">Đã xử lý</Badge>);
    expect(screen.getByTestId("status-badge")).toHaveTextContent("Đã xử lý");
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <div>
        <Badge tone="neutral">Mặc định</Badge>
        <Badge tone="warning">Cảnh báo</Badge>
        <Badge tone="danger">Lỗi</Badge>
      </div>,
    );
    await expectNoA11yViolations(container);
  });
});
