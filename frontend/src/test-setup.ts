import "@testing-library/jest-dom/vitest";
import { expect } from "vitest";
import { toHaveNoViolations } from "jest-axe";

// axe-core smoke testing (T-106 §5.11 / §7): mọi test có thể gọi
// `expect(await axe(container)).toHaveNoViolations()`.
expect.extend(toHaveNoViolations);
