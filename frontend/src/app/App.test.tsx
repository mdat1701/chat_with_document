import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "@app/App";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        const body = url.includes("/documents")
          ? []
          : {
              id: "11111111-1111-1111-1111-111111111111",
              email: "user@example.com",
              display_name: "User",
              roles: [],
              csrf_token: "token",
            };
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("hiển thị trạng thái đang tải trước khi xác thực xong", () => {
    render(<App />);
    expect(screen.getByTestId("route-placeholder")).toHaveTextContent(
      "Đang tải",
    );
  });

  it("hiển thị thư viện tài liệu sau khi xác thực thành công", async () => {
    render(<App />);
    await waitFor(() =>
      expect(screen.getByTestId("route-placeholder")).toHaveTextContent(
        "SCR-02",
      ),
    );
  });
});
