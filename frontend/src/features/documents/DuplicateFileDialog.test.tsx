import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { DuplicateFileDialog } from "./DuplicateFileDialog";

describe("DuplicateFileDialog", () => {
  it("hiển thị tên tệp trùng và 3 lựa chọn", () => {
    render(
      <DuplicateFileDialog
        fileName="HopDong.pdf"
        onReplace={vi.fn()}
        onKeepBoth={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("duplicate-file-dialog")).toHaveTextContent(
      "HopDong.pdf",
    );
    expect(screen.getByTestId("duplicate-replace")).toBeInTheDocument();
    expect(screen.getByTestId("duplicate-keep-both")).toBeInTheDocument();
    expect(screen.getByTestId("duplicate-cancel")).toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { baseElement } = render(
      <DuplicateFileDialog
        fileName="HopDong.pdf"
        onReplace={vi.fn()}
        onKeepBoth={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    await expectNoA11yViolations(baseElement);
  });
});
