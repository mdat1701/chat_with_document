// jest-axe chỉ augment namespace `jest`, không augment `vitest`. Khai báo
// thủ công để `expect(await axe(container)).toHaveNoViolations()` có kiểu.
import "vitest";

declare module "vitest" {
  interface Assertion {
    toHaveNoViolations(): void;
  }
  interface AsymmetricMatchersContaining {
    toHaveNoViolations(): void;
  }
}
