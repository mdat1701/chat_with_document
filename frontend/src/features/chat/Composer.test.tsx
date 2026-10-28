import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { Composer } from "./Composer";

describe("Composer", () => {
  it("hiển thị ô nhập và bộ đếm ký tự", () => {
    render(
      <Composer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        maxLength={2000}
      />,
    );
    expect(screen.getByTestId("question-input")).toBeInTheDocument();
    expect(screen.getByTestId("char-counter")).toHaveTextContent("0/2.000");
  });

  it("khóa toàn bộ ô nhập khi có disabledReason khác awaiting_answer", () => {
    render(
      <Composer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        maxLength={2000}
        disabledReason="no_docs"
      />,
    );
    expect(screen.getByTestId("question-input")).toBeDisabled();
  });

  it("không có vi phạm a11y nghiêm trọng (trạng thái sẵn sàng)", async () => {
    const { container } = render(
      <Composer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        maxLength={2000}
      />,
    );
    await expectNoA11yViolations(container);
  });

  it("không có vi phạm a11y nghiêm trọng khi khóa kèm tooltip", async () => {
    const { container } = render(
      <Composer
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        maxLength={2000}
        disabledReason="offline"
      />,
    );
    await expectNoA11yViolations(container);
  });
});
