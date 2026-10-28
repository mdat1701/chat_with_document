// jest-axe không kèm file khai báo kiểu (T-106 §5.11). Khai báo ambient
// module tối thiểu ở đây. Lưu ý: file này KHÔNG được có `import`/`export`
// ở cấp cao nhất — nếu có, TypeScript coi đây là "mở rộng" một module đã
// tồn tại thay vì khai báo module mới, và phần khai báo bên dưới sẽ bị bỏ
// qua một cách âm thầm.
declare module "jest-axe" {
  export function axe(html: Element | string, options?: unknown): Promise<unknown>;
  export const toHaveNoViolations: {
    toHaveNoViolations: (results: unknown) => { pass: boolean; message: () => string };
  };
}
