import { describe, expect, it } from "vitest";
import { formatCitation, formatCitationPage } from "./citations";

// T-402 §7 — unit test cho formatCitationPage (4 nhánh) và formatCitation
// (bao gồm nhánh feature flag tắt).
describe("formatCitationPage", () => {
  it("trả null khi không có page_start", () => {
    expect(formatCitationPage(null, null)).toBeNull();
    expect(formatCitationPage(undefined, undefined)).toBeNull();
  });

  it("trả 'tr. N' khi start === end", () => {
    expect(formatCitationPage(12, 12)).toBe("tr. 12");
  });

  it("trả 'tr. N' khi end bị thiếu", () => {
    expect(formatCitationPage(12, null)).toBe("tr. 12");
  });

  it("trả 'tr. N–M' (en dash) khi start !== end", () => {
    expect(formatCitationPage(3, 4)).toBe("tr. 3–4");
  });
});

describe("formatCitation", () => {
  it("AC-015.1: nối tên tệp và số trang khi bật flag", () => {
    expect(formatCitation("HopDong.pdf", 12, 12)).toBe("HopDong.pdf · tr. 12");
  });

  it("AC-015.3: chỉ tên tệp khi thiếu số trang, không có 'undefined'", () => {
    const result = formatCitation("TaiLieu.pdf", null, null);
    expect(result).toBe("TaiLieu.pdf");
    expect(result).not.toContain("undefined");
    expect(result).not.toContain("·");
  });

  it("Tắt feature flag citation_page_numbers → chỉ tên tệp dù có số trang", () => {
    expect(formatCitation("PhuLuc.pdf", 3, 4, false)).toBe("PhuLuc.pdf");
  });
});
