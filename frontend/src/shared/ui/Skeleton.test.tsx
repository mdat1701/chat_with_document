import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Skeleton } from "./Skeleton";
import { expectNoA11yViolations } from "@shared/testing/axe";

describe("Skeleton", () => {
  it("ẩn khỏi cây hỗ trợ tiếp cận (aria-hidden)", () => {
    const { getByTestId } = render(<Skeleton data-testid="doc-skeleton" width={200} height={20} />);
    expect(getByTestId("doc-skeleton")).toHaveAttribute("aria-hidden", "true");
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(<Skeleton width="100%" height="2rem" />);
    await expectNoA11yViolations(container);
  });
});
