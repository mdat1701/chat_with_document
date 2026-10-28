import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  DRAFT_STORAGE_KEY,
  captureDraftOnUnauthorized,
  clearDraft,
  registerComposerSource,
  restoreDraft,
  saveDraft,
} from "./draft";

describe("features/auth/draft (AC-001.3)", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  afterEach(() => {
    registerComposerSource(null);
    vi.restoreAllMocks();
  });

  it("lưu và khôi phục nguyên vẹn nội dung composer", () => {
    saveDraft("Tài liệu này nói gì về điều khoản bảo mật?");
    expect(restoreDraft()).toBe("Tài liệu này nói gì về điều khoản bảo mật?");
    expect(window.sessionStorage.getItem(DRAFT_STORAGE_KEY)).not.toBeNull();
  });

  it("không lưu nếu nội dung rỗng hoặc chỉ có khoảng trắng", () => {
    saveDraft("   ");
    expect(restoreDraft()).toBeNull();
  });

  it("cắt khoảng trắng đầu/cuối trước khi lưu", () => {
    saveDraft("  câu hỏi có khoảng trắng  ");
    expect(restoreDraft()).toBe("câu hỏi có khoảng trắng");
  });

  it("xóa bản nháp sau khi khôi phục thành công", () => {
    saveDraft("nội dung nháp");
    clearDraft();
    expect(restoreDraft()).toBeNull();
  });

  it("restoreDraft trả về null khi chưa từng lưu gì", () => {
    expect(restoreDraft()).toBeNull();
  });

  it("captureDraftOnUnauthorized lưu nội dung đang soạn từ composer đã đăng ký", () => {
    registerComposerSource(() => "câu hỏi đang gõ dở");
    captureDraftOnUnauthorized();
    expect(restoreDraft()).toBe("câu hỏi đang gõ dở");
  });

  it("captureDraftOnUnauthorized không làm gì nếu không có composer nào đăng ký", () => {
    captureDraftOnUnauthorized();
    expect(restoreDraft()).toBeNull();
  });

  it("captureDraftOnUnauthorized không lưu khi composer đang rỗng", () => {
    registerComposerSource(() => "   ");
    captureDraftOnUnauthorized();
    expect(restoreDraft()).toBeNull();
  });

  it("chế độ ẩn danh chặn sessionStorage: saveDraft/restoreDraft/clearDraft không ném lỗi", () => {
    const getItem = vi.spyOn(window.sessionStorage.__proto__, "getItem").mockImplementation(() => {
      throw new DOMException("blocked");
    });
    const setItem = vi.spyOn(window.sessionStorage.__proto__, "setItem").mockImplementation(() => {
      throw new DOMException("blocked");
    });
    const removeItem = vi
      .spyOn(window.sessionStorage.__proto__, "removeItem")
      .mockImplementation(() => {
        throw new DOMException("blocked");
      });

    expect(() => saveDraft("nội dung")).not.toThrow();
    expect(() => restoreDraft()).not.toThrow();
    expect(() => clearDraft()).not.toThrow();
    expect(restoreDraft()).toBeNull();

    getItem.mockRestore();
    setItem.mockRestore();
    removeItem.mockRestore();
  });
});
