import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppConfigProvider } from "@shared/config";
import { DEFAULT_APP_CONFIG } from "@shared/config/appConfig";
import { ToastProvider, ToastRegion } from "@shared/ui";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { DocumentLibrary } from "./DocumentLibrary";

vi.mock("@shared/analytics/client", () => ({ track: vi.fn(), flush: vi.fn() }));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFetchMock(documents: unknown[]) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/config")) return jsonResponse(DEFAULT_APP_CONFIG);
      if (url.endsWith("/documents")) return jsonResponse(documents);
      return jsonResponse({});
    }),
  );
}

async function renderLibrary() {
  const utils = render(
    <AppConfigProvider>
      <ToastProvider>
        <DocumentLibrary />
        <ToastRegion />
      </ToastProvider>
    </AppConfigProvider>,
  );
  await waitFor(() =>
    expect(screen.queryByTestId("documents-skeleton")).not.toBeInTheDocument(),
  );
  return utils;
}

describe("DocumentLibrary", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("ES-01: không có tài liệu nào → trạng thái trống", async () => {
    installFetchMock([]);
    await renderLibrary();
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });

  it("hiển thị danh sách tài liệu khi có dữ liệu", async () => {
    installFetchMock([
      {
        id: "d1",
        name: "HopDong.pdf",
        size_bytes: 1024,
        page_count: 10,
        status: "ready",
        error_code: null,
      },
    ]);
    await renderLibrary();
    expect(screen.getByTestId("doc-list")).toHaveTextContent("HopDong.pdf");
  });

  it("không có vi phạm a11y nghiêm trọng (trạng thái trống)", async () => {
    installFetchMock([]);
    const { container } = await renderLibrary();
    await expectNoA11yViolations(container);
  });

  it("không có vi phạm a11y nghiêm trọng (danh sách có tài liệu)", async () => {
    installFetchMock([
      {
        id: "d1",
        name: "HopDong.pdf",
        size_bytes: 1024,
        page_count: 10,
        status: "ready",
        error_code: null,
      },
      {
        id: "d2",
        name: "BaoCao.pdf",
        size_bytes: 2048,
        page_count: 5,
        status: "failed",
        error_code: "INGESTION_FAILED",
      },
    ]);
    const { container } = await renderLibrary();
    await expectNoA11yViolations(container);
  });

  it("T-405 §5.6: ArrowDown/ArrowUp duyệt qua các dòng tài liệu", async () => {
    installFetchMock([
      {
        id: "d1",
        name: "HopDong.pdf",
        size_bytes: 1024,
        page_count: 10,
        status: "ready",
        error_code: null,
      },
      {
        id: "d2",
        name: "BaoCao.pdf",
        size_bytes: 2048,
        page_count: 5,
        status: "ready",
        error_code: null,
      },
    ]);
    await renderLibrary();
    const rows = screen.getAllByTestId("doc-item");
    expect(rows).toHaveLength(2);
    rows[0].focus();
    expect(document.activeElement).toBe(rows[0]);
    fireEvent.keyDown(screen.getByTestId("doc-list"), { key: "ArrowDown" });
    expect(document.activeElement).toBe(rows[1]);
    fireEvent.keyDown(screen.getByTestId("doc-list"), { key: "ArrowDown" });
    expect(document.activeElement).toBe(rows[1]);
    fireEvent.keyDown(screen.getByTestId("doc-list"), { key: "ArrowUp" });
    expect(document.activeElement).toBe(rows[0]);
  });
});
