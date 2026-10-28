import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("hiển thị icon và chữ cho trạng thái failed kèm lý do", () => {
    render(<StatusBadge status="failed" errorCode="UPLOAD_NETWORK" />);
    const badge = screen.getByTestId("doc-status");
    expect(badge).toHaveTextContent("Lỗi");
    expect(badge).toHaveAccessibleName(/Lỗi/);
  });

  it("không có vi phạm a11y nghiêm trọng ở mọi trạng thái", async () => {
    const { container, rerender } = render(
      <StatusBadge status="uploading" progress={40} />,
    );
    await expectNoA11yViolations(container);

    rerender(<StatusBadge status="processing" />);
    await expectNoA11yViolations(container);

    rerender(<StatusBadge status="ready" />);
    await expectNoA11yViolations(container);

    rerender(<StatusBadge status="failed" errorCode="INGESTION_FAILED" />);
    await expectNoA11yViolations(container);
  });
});
