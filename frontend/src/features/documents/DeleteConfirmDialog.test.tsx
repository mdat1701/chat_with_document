import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { DeleteConfirmDialog } from "./DeleteConfirmDialog";

describe("DeleteConfirmDialog", () => {
  it("hiển thị tên tệp trong mô tả", () => {
    render(
      <DeleteConfirmDialog
        open
        fileName="HopDong.pdf"
        pending={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("delete-confirm")).toHaveTextContent(
      "HopDong.pdf",
    );
  });

  it("không render khi open=false", () => {
    render(
      <DeleteConfirmDialog
        open={false}
        fileName="HopDong.pdf"
        pending={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("delete-confirm")).not.toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng khi mở", async () => {
    const { baseElement } = render(
      <DeleteConfirmDialog
        open
        fileName="HopDong.pdf"
        pending={false}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await expectNoA11yViolations(baseElement);
  });
});
