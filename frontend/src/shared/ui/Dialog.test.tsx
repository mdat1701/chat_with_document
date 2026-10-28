import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Dialog } from "./Dialog";
import { Button } from "./Button";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Dialog", () => {
  it("hiển thị tiêu đề và mô tả khi open=true", () => {
    render(
      <Dialog
        open
        onOpenChange={vi.fn()}
        title="Xóa tài liệu?"
        description="Hành động không thể hoàn tác."
        data-testid="confirm-dialog"
      >
        <Button data-testid="confirm">Xóa</Button>
      </Dialog>,
    );
    expect(screen.getByTestId("confirm-dialog")).toBeInTheDocument();
    expect(screen.getByText("Xóa tài liệu?")).toBeInTheDocument();
  });

  it("không render nội dung khi open=false", () => {
    render(
      <Dialog
        open={false}
        onOpenChange={vi.fn()}
        title="Xóa tài liệu?"
        data-testid="confirm-dialog"
      />,
    );
    expect(screen.queryByTestId("confirm-dialog")).not.toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng khi mở", async () => {
    const { baseElement } = render(
      <Dialog
        open
        onOpenChange={vi.fn()}
        title="Xóa tài liệu?"
        description="Hành động không thể hoàn tác."
        actions={
          <Button variant="danger" data-testid="confirm">
            Xóa
          </Button>
        }
      />,
    );
    await expectNoA11yViolations(baseElement);
  });
});
