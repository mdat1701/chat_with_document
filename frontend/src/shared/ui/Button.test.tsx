import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Button } from "./Button";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Button", () => {
  it("hiển thị nhãn và chuyển tiếp data-testid", () => {
    render(<Button data-testid="submit-button">Gửi</Button>);
    expect(screen.getByTestId("submit-button")).toHaveTextContent("Gửi");
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <>
        <Button data-testid="primary">Lưu</Button>
        <Button variant="secondary" data-testid="secondary">
          Hủy
        </Button>
        <Button variant="danger" disabled data-testid="danger">
          Xóa
        </Button>
      </>,
    );
    await expectNoA11yViolations(container);
  });
});
