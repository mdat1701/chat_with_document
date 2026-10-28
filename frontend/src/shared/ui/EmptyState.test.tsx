import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState } from "./EmptyState";
import { Button } from "./Button";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("EmptyState", () => {
  it("hiển thị tiêu đề và mô tả", () => {
    render(
      <EmptyState
        data-testid="empty-docs"
        title="Chưa có tài liệu"
        description="Hãy tải PDF đầu tiên."
      />,
    );
    expect(screen.getByTestId("empty-docs")).toHaveTextContent(
      "Chưa có tài liệu",
    );
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <EmptyState
        title="Chưa có tài liệu"
        description="Hãy tải PDF đầu tiên."
        action={<Button data-testid="upload-cta">Tải lên</Button>}
      />,
    );
    await expectNoA11yViolations(container);
  });
});
