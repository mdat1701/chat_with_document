import { describe, expect, it } from "vitest";
import { daysUntil, resolveEmptyState } from "./emptyState";
import type { DocumentStatus } from "./types";

const doc = (status: DocumentStatus) => ({ status });

describe("resolveEmptyState", () => {
  it("ES-01: không có tài liệu, chưa có hội thoại", () => {
    expect(resolveEmptyState([], false)).toBe("ES-01");
  });

  it("ES-05: không có tài liệu nhưng đã có hội thoại cũ", () => {
    expect(resolveEmptyState([], true)).toBe("ES-05");
  });

  it("ES-02: có tài liệu nhưng tất cả đang xử lý/tải lên", () => {
    expect(
      resolveEmptyState([doc("processing"), doc("uploading")], false),
    ).toBe("ES-02");
  });

  it("ES-03: có tài liệu nhưng tất cả thất bại", () => {
    expect(resolveEmptyState([doc("failed"), doc("failed")], false)).toBe(
      "ES-03",
    );
  });

  it("ES-04: có tài liệu sẵn sàng nhưng chưa có câu hỏi nào", () => {
    expect(resolveEmptyState([doc("ready"), doc("processing")], false)).toBe(
      "ES-04",
    );
  });

  it("null khi có tài liệu sẵn sàng và đã có hội thoại", () => {
    expect(resolveEmptyState([doc("ready")], true)).toBeNull();
  });
});

describe("daysUntil", () => {
  it("trả về null khi không có ngày", () => {
    expect(daysUntil(undefined)).toBeNull();
  });

  it("tính đúng số ngày còn lại", () => {
    const inSevenDays = new Date();
    inSevenDays.setDate(inSevenDays.getDate() + 7);
    expect(daysUntil(inSevenDays.toISOString())).toBe(7);
  });

  it("ngày quá hạn vẫn trả về số âm (UI tự diễn giải thành 'hôm nay')", () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    expect(daysUntil(yesterday.toISOString())).toBeLessThan(0);
  });
});
