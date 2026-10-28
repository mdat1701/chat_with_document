import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Tooltip } from "./Tooltip";
import { IconButton } from "./IconButton";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Tooltip", () => {
  it("hiển thị phần tử kích hoạt", () => {
    render(
      <Tooltip content="Tải xuống tệp">
        <IconButton label="Tải xuống" icon={<span aria-hidden>⬇</span>} data-testid="download-button" />
      </Tooltip>,
    );
    expect(screen.getByTestId("download-button")).toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <Tooltip content="Tải xuống tệp">
        <IconButton label="Tải xuống" icon={<span aria-hidden>⬇</span>} data-testid="download-button" />
      </Tooltip>,
    );
    await expectNoA11yViolations(container);
  });
});
