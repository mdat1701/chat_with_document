import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ToastProvider, ToastRegion, useToast } from "./Toast";
import { expectNoA11yViolations } from "@shared/testing/axe";

function Trigger() {
  const { showToast } = useToast();
  return (
    <button
      type="button"
      data-testid="trigger"
      onClick={() => showToast({ title: "Đã lưu", tone: "success" })}
    >
      Lưu
    </button>
  );
}

describe("ToastRegion", () => {
  it("hiển thị toast sau khi showToast được gọi", () => {
    render(
      <ToastProvider>
        <Trigger />
        <ToastRegion data-testid="toast-region" />
      </ToastProvider>,
    );
    act(() => screen.getByTestId("trigger").click());
    expect(screen.getByTestId("toast-item")).toHaveTextContent("Đã lưu");
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <ToastProvider>
        <Trigger />
        <ToastRegion data-testid="toast-region" />
      </ToastProvider>,
    );
    act(() => screen.getByTestId("trigger").click());
    await expectNoA11yViolations(container);
  });
});
