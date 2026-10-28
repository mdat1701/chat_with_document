import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OfflineBanner } from "./OfflineBanner";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("OfflineBanner", () => {
  it("không render gì khi offline=false", () => {
    render(<OfflineBanner offline={false} message="Bạn đang ngoại tuyến" />);
    expect(screen.queryByTestId("offline-banner")).not.toBeInTheDocument();
  });

  it("hiển thị thông báo khi offline=true", () => {
    render(<OfflineBanner offline message="Bạn đang ngoại tuyến" />);
    const banner = screen.getByTestId("offline-banner");
    expect(banner).toHaveTextContent("Bạn đang ngoại tuyến");
    expect(banner).toHaveAttribute("role", "status");
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <OfflineBanner offline message="Bạn đang ngoại tuyến" />,
    );
    await expectNoA11yViolations(container);
  });
});
