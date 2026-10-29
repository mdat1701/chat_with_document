import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mỗi test cần một bản module riêng (vi.resetModules) vì client.ts đăng
// ký một `setInterval` ở cấp module (chạy một lần duy nhất khi import) —
// dùng chung instance giữa các test sẽ làm trạng thái `queue` và lịch
// chạy của interval rò rỉ qua nhau.
async function freshClient() {
  vi.resetModules();
  return import("./client");
}

describe("analytics client", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response(null, { status: 204 }))),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("flushes automatically after the time-based interval even with few events (T-404 §5 bước 5)", async () => {
    const { track } = await freshClient();
    track("document_upload_started", { file_size_bucket: "small" });
    expect(fetch).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(5000);

    expect(fetch).toHaveBeenCalledTimes(1);
    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.events).toHaveLength(1);
    expect(body.events[0].event_name).toBe("document_upload_started");
  });

  it("flushes immediately once 20 events accumulate, without waiting for the timer", async () => {
    const { track } = await freshClient();
    for (let i = 0; i < 20; i++) {
      track("citation_viewed", { citation_index: i });
    }
    await Promise.resolve();
    expect(fetch).toHaveBeenCalledTimes(1);
    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.events).toHaveLength(20);
  });

  it("flush() is a no-op when the queue is empty", async () => {
    const { flush } = await freshClient();
    await flush();
    expect(fetch).not.toHaveBeenCalled();
  });
});
