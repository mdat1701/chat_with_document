import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Drawer } from "./Drawer";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Drawer", () => {
  it("hiển thị tiêu đề và nội dung khi open=true", () => {
    render(
      <Drawer open onOpenChange={vi.fn()} title="Tài liệu của bạn" closeLabel="Đóng" data-testid="document-drawer">
        <p>Nội dung ngăn</p>
      </Drawer>,
    );
    expect(screen.getByTestId("document-drawer")).toBeInTheDocument();
    expect(screen.getByText("Tài liệu của bạn")).toBeInTheDocument();
  });

  it("không render nội dung khi open=false", () => {
    render(<Drawer open={false} onOpenChange={vi.fn()} title="Tài liệu của bạn" closeLabel="Đóng" data-testid="document-drawer" />);
    expect(screen.queryByTestId("document-drawer")).not.toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng khi mở", async () => {
    const { baseElement } = render(
      <Drawer open onOpenChange={vi.fn()} title="Tài liệu của bạn" closeLabel="Đóng" data-testid="document-drawer">
        <p>Nội dung ngăn</p>
      </Drawer>,
    );
    await expectNoA11yViolations(baseElement);
  });
});
