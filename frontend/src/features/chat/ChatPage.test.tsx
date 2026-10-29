import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppConfigProvider } from "@shared/config";
import { DEFAULT_APP_CONFIG, type AppConfig } from "@shared/config/appConfig";
import { ToastProvider, ToastRegion } from "@shared/ui";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { ChatPage } from "./ChatPage";

vi.mock("@shared/analytics/client", () => ({ track: vi.fn(), flush: vi.fn() }));
const { track } = await import("@shared/analytics/client");

type FetchMockOptions = {
  documents?: Array<{ id: string; status: string }>;
  config?: Partial<AppConfig>;
  sseEvents?: string[];
  questionResponse?: () => Response;
};

function sseStream(events: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < events.length) {
        controller.enqueue(encoder.encode(events[i]));
        i += 1;
      } else {
        controller.close();
      }
    },
  });
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installFetchMock(options: FetchMockOptions) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/config"))
        return jsonResponse({ ...DEFAULT_APP_CONFIG, ...options.config });
      if (url.endsWith("/documents"))
        return jsonResponse(options.documents ?? []);
      if (url.endsWith("/conversations") && init?.method === "POST") {
        return jsonResponse({
          conversation_id: "11111111-1111-1111-1111-111111111111",
        });
      }
      if (url.includes("/questions")) {
        if (options.questionResponse) return options.questionResponse();
        return new Response(sseStream(options.sseEvents ?? []), {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        });
      }
      return jsonResponse({});
    }),
  );
}

async function renderChat(onHasMessagesChange?: (has: boolean) => void) {
  const utils = render(
    <AppConfigProvider>
      <ToastProvider>
        <ChatPage onHasMessagesChange={onHasMessagesChange} />
        <ToastRegion />
      </ToastProvider>
    </AppConfigProvider>,
  );
  await waitFor(() =>
    expect(
      screen.queryByTestId("chat-loading-skeleton"),
    ).not.toBeInTheDocument(),
  );
  return utils;
}

describe("ChatPage", () => {
  beforeEach(() => {
    vi.useRealTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it("AC-011.3: khóa composer khi chưa có tài liệu sẵn sàng", async () => {
    installFetchMock({ documents: [] });
    await renderChat();
    expect(screen.getByTestId("question-input")).toBeDisabled();
    expect(screen.getByTestId("send-button")).toBeDisabled();
  });

  it("ER-09: câu hỏi vượt quá giới hạn → bộ đếm đỏ, nút Gửi khóa", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      config: { max_question_length: 10 },
    });
    await renderChat();
    const input = screen.getByTestId("question-input");
    fireEvent.change(input, {
      target: { value: "0123456789-vuot-qua-gioi-han" },
    });
    expect(screen.getByTestId("char-counter")).toHaveClass(
      "chat-char-counter--danger",
    );
    expect(screen.getByTestId("send-button")).toBeDisabled();
  });

  it("AC-011.4: chỉ gõ khoảng trắng → Gửi không làm gì", async () => {
    installFetchMock({ documents: [{ id: "d1", status: "ready" }] });
    await renderChat();
    const input = screen.getByTestId("question-input");
    fireEvent.change(input, { target: { value: "   " } });
    expect(screen.getByTestId("send-button")).toBeDisabled();
  });

  it("gửi câu hỏi: tối ưu (optimistic) hiện ngay TypingIndicator, rồi render câu trả lời đầy đủ kèm thẻ nguồn", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: meta\ndata: {"answer_id":"a1","ready_doc_count":1}\n\n',
        'event: delta\ndata: {"text":"Xin chào "}\n\n',
        'event: delta\ndata: {"text":"[1]."}\n\n',
        'event: citations\ndata: {"items":[{"index":1,"document_id":"d1","document_name":"HopDong.pdf","page_start":12,"page_end":12}]}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":1800,"uncited":false}\n\n',
      ],
    });
    await renderChat();
    const input = screen.getByTestId("question-input");
    fireEvent.change(input, {
      target: { value: "Hợp đồng có hiệu lực đến khi nào?" },
    });
    fireEvent.click(screen.getByTestId("send-button"));

    // Optimistic: tin nhắn người dùng + TypingIndicator xuất hiện ngay (IX-03).
    expect(screen.getByTestId("user-message")).toHaveTextContent(
      "Hợp đồng có hiệu lực đến khi nào?",
    );
    expect(screen.getByTestId("typing-indicator")).toHaveTextContent("1");

    await waitFor(() =>
      expect(screen.getByTestId("citation-list")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("answer-markdown")).toHaveTextContent("Xin chào");
    const chip = screen.getByTestId("citation-chip");
    expect(chip).toHaveTextContent("HopDong.pdf");
    expect(chip).toHaveTextContent("tr. 12");
    expect(screen.getByTestId("answer-latency")).toHaveTextContent("1,8");

    expect(track).toHaveBeenCalledWith(
      "question_submitted",
      expect.objectContaining({
        ready_doc_count: 1,
        question_length: expect.any(Number),
      }),
    );
    // T-404 §5.4: `answer_rendered` được backend phát trực tiếp (conversations.py)
    // để latency_ms chính xác — FE không phát lại, tránh đếm trùng.
    expect(track).not.toHaveBeenCalledWith(
      "answer_rendered",
      expect.anything(),
    );
  });

  it("IR-04: nội dung <script> bị rehype-sanitize loại bỏ, không thực thi", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: delta\ndata: {"text":"An toàn <script>window.__xss=true;</script> nội dung."}\n\n',
        'event: citations\ndata: {"items":[]}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":100,"uncited":true}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi bất kỳ đủ dài" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("answer-latency")).toBeInTheDocument(),
    );
    expect(document.querySelector("script")).toBeNull();
    expect((window as unknown as { __xss?: boolean }).__xss).toBeUndefined();
    // IR-02: answered nhưng citations rỗng → cảnh báo không xác định nguồn.
    expect(screen.getByTestId("uncited-warning")).toBeInTheDocument();
  });

  it("AC-013.1/AC-014.4: done.type=not_found → NotFoundMessage, không thẻ nguồn", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: citations\ndata: {"items":[]}\n\n',
        'event: done\ndata: {"type":"not_found","latency_ms":900}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi không có đáp án nào cả" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("not-found-message")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("citation-list")).not.toBeInTheDocument();
  });

  it("ANSWER_INTERRUPTED sau khi đã có delta → incomplete: nội dung mờ, ẩn thẻ nguồn (IR-01)", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: delta\ndata: {"text":"Nội dung nhận được trước khi đứt."}\n\n',
        'event: error\ndata: {"code":"ANSWER_INTERRUPTED"}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi sẽ bị gián đoạn giữa chừng" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("incomplete-note")).toBeInTheDocument(),
    );
    const answer = screen.getByTestId("answer-message");
    expect(answer).toHaveAttribute("data-phase", "incomplete");
    expect(screen.queryByTestId("citation-list")).not.toBeInTheDocument();
    expect(screen.getByTestId("retry-button")).toBeInTheDocument();
  });

  it("error trước delta đầu tiên → failed; bấm Thử lại gửi lại đúng câu hỏi cũ", async () => {
    let questionCalls = 0;
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      questionResponse: () => {
        questionCalls += 1;
        return new Response(
          sseStream(['event: error\ndata: {"code":"SERVICE_BUSY"}\n\n']),
          {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
          },
        );
      },
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi sẽ gặp lỗi SERVICE_BUSY" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("error-message")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("error-message")).toHaveTextContent(
      "Dịch vụ đang bận",
    );
    expect(questionCalls).toBe(1);

    fireEvent.click(screen.getByTestId("retry-button"));
    await waitFor(() => expect(questionCalls).toBe(2));
    expect(track).toHaveBeenCalledWith(
      "retry_clicked",
      expect.objectContaining({ context: "failed" }),
    );
  });

  it("T-402: tắt citation_page_numbers → chip chỉ hiện tên tệp, không có 'tr.'", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      config: { features: { citation_page_numbers: false } },
      sseEvents: [
        'event: delta\ndata: {"text":"Nội dung [1]."}\n\n',
        'event: citations\ndata: {"items":[{"index":1,"document_id":"d1","document_name":"HopDong.pdf","page_start":12,"page_end":12}]}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":500,"uncited":false}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi có trích dẫn trang" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("citation-chip")).toBeInTheDocument(),
    );
    const chip = screen.getByTestId("citation-chip");
    expect(chip).toHaveTextContent("HopDong.pdf");
    expect(chip).not.toHaveTextContent("tr.");
  });

  it("T-404: citation_viewed phát khi hover ≥500ms, không phát nếu rời chuột sớm hơn", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: citations\ndata: {"items":[{"index":1,"document_id":"d1","document_name":"HopDong.pdf","page_start":1,"page_end":1}]}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":100,"uncited":false}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi có trích dẫn để hover" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("citation-chip")).toBeInTheDocument(),
    );
    const chip = screen.getByTestId("citation-chip");

    vi.useFakeTimers();
    fireEvent.mouseEnter(chip);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    fireEvent.mouseLeave(chip);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(track).not.toHaveBeenCalledWith(
      "citation_viewed",
      expect.anything(),
    );

    fireEvent.mouseEnter(chip);
    act(() => {
      vi.advanceTimersByTime(500);
    });
    expect(track).toHaveBeenCalledWith("citation_viewed", {
      citation_index: 1,
    });
    vi.useRealTimers();
  });

  it("CitationRef [n] không khớp thẻ nguồn nào → chữ thường, không liên kết (IR-03)", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: delta\ndata: {"text":"Tham chiếu không khớp [5]."}\n\n',
        'event: citations\ndata: {"items":[{"index":1,"document_id":"d1","document_name":"HopDong.pdf"}]}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":100,"uncited":false}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi có trích dẫn không khớp" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("citation-list")).toBeInTheDocument(),
    );
    expect(
      within(screen.getByTestId("answer-markdown")).queryByTestId(
        "citation-ref",
      ),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("answer-markdown")).toHaveTextContent("[5]");
  });

  it("T-405 §5.6: Ctrl+Shift+O xóa lịch sử hội thoại và trả focus về ô câu hỏi", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: delta\ndata: {"text":"Nội dung."}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":100,"uncited":true}\n\n',
      ],
    });
    await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi đầu tiên" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("user-message")).toBeInTheDocument(),
    );

    fireEvent.keyDown(document, {
      key: "O",
      ctrlKey: true,
      shiftKey: true,
    });

    expect(screen.queryByTestId("user-message")).not.toBeInTheDocument();
    expect(screen.getByTestId("question-input")).toHaveFocus();
  });

  it("T-305/T-306: không có vi phạm a11y nghiêm trọng (trạng thái ban đầu)", async () => {
    installFetchMock({ documents: [{ id: "d1", status: "ready" }] });
    const { container } = await renderChat();
    await expectNoA11yViolations(container);
  });

  it("T-305/T-306: không có vi phạm a11y nghiêm trọng (có câu trả lời + trích dẫn)", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: delta\ndata: {"text":"Nội dung trả lời [1]."}\n\n',
        'event: citations\ndata: {"items":[{"index":1,"document_id":"d1","document_name":"HopDong.pdf","page_start":1,"page_end":1}]}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":100,"uncited":false}\n\n',
      ],
    });
    const { container } = await renderChat();
    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi có đáp án và trích dẫn" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(screen.getByTestId("citation-list")).toBeInTheDocument(),
    );
    await expectNoA11yViolations(container);
  });

  it("T-208 ES-05: báo onHasMessagesChange(true) sau câu hỏi đầu, (false) khi xóa lịch sử", async () => {
    installFetchMock({
      documents: [{ id: "d1", status: "ready" }],
      sseEvents: [
        'event: delta\ndata: {"text":"Nội dung."}\n\n',
        'event: done\ndata: {"type":"answered","latency_ms":100,"uncited":true}\n\n',
      ],
    });
    const onHasMessagesChange = vi.fn();
    await renderChat(onHasMessagesChange);
    expect(onHasMessagesChange).toHaveBeenLastCalledWith(false);

    fireEvent.change(screen.getByTestId("question-input"), {
      target: { value: "Câu hỏi đầu tiên" },
    });
    fireEvent.click(screen.getByTestId("send-button"));
    await waitFor(() =>
      expect(onHasMessagesChange).toHaveBeenLastCalledWith(true),
    );

    fireEvent.keyDown(document, { key: "O", ctrlKey: true, shiftKey: true });
    await waitFor(() =>
      expect(onHasMessagesChange).toHaveBeenLastCalledWith(false),
    );
  });
});
