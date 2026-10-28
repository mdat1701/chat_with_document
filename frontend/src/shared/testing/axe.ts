// Trợ giúp kiểm thử khói a11y cho shared/ui (T-106 §5.11 / §7).
// Dùng trong *.test.tsx: `await expectNoA11yViolations(container)`.
import { axe } from "jest-axe";
import { expect } from "vitest";

export async function expectNoA11yViolations(container: Element) {
  const results = await axe(container);
  expect(results).toHaveNoViolations();
}
