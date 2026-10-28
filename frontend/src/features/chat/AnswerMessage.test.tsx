import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { AnswerMessage } from "./AnswerMessage";
import type { AnswerVM } from "./types";

function renderAnswer(answer: AnswerVM) {
  return render(
    <AnswerMessage
      answer={answer}
      readyDocCount={1}
      showPageNumbers
      onRetry={vi.fn()}
    />,
  );
}

describe("AnswerMessage", () => {
  it("phase=pending hiển thị chỉ báo đang gõ", () => {
    renderAnswer({ id: "a1", phase: "pending", markdown: "", citations: [] });
    expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
  });

  it("phase=complete hiển thị markdown và thẻ nguồn", () => {
    renderAnswer({
      id: "a2",
      phase: "complete",
      type: "answered",
      markdown: "Xin chào [1].",
      citations: [
        {
          index: 1,
          documentId: "d1",
          documentName: "HopDong.pdf",
          pageStart: 1,
          pageEnd: 1,
        },
      ],
      latencyMs: 1200,
    });
    expect(screen.getByTestId("citation-list")).toBeInTheDocument();
    expect(screen.getByTestId("answer-markdown")).toHaveTextContent("Xin chào");
  });

  it("phase=failed hiển thị thông báo lỗi và nút thử lại", () => {
    renderAnswer({
      id: "a3",
      phase: "failed",
      markdown: "",
      citations: [],
      errorCode: "SERVICE_BUSY",
    });
    expect(screen.getByTestId("error-message")).toBeInTheDocument();
    expect(screen.getByTestId("retry-button")).toBeInTheDocument();
  });

  it("not_found hiển thị thông báo riêng, không có thẻ nguồn", () => {
    renderAnswer({
      id: "a4",
      phase: "complete",
      type: "not_found",
      markdown: "",
      citations: [],
    });
    expect(screen.getByTestId("not-found-message")).toBeInTheDocument();
    expect(screen.queryByTestId("citation-list")).not.toBeInTheDocument();
  });

  it("phase=incomplete hiển thị ghi chú và nút thử lại", () => {
    renderAnswer({
      id: "a5",
      phase: "incomplete",
      markdown: "Nội dung dang dở.",
      citations: [],
    });
    expect(screen.getByTestId("incomplete-note")).toBeInTheDocument();
    expect(screen.getByTestId("retry-button")).toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng ở mọi phase chính", async () => {
    const { container, rerender } = renderAnswer({
      id: "a6",
      phase: "pending",
      markdown: "",
      citations: [],
    });
    await expectNoA11yViolations(container);

    rerender(
      <AnswerMessage
        answer={{
          id: "a6",
          phase: "complete",
          type: "answered",
          markdown: "Nội dung [1].",
          citations: [
            {
              index: 1,
              documentId: "d1",
              documentName: "HopDong.pdf",
              pageStart: 1,
              pageEnd: 1,
            },
          ],
          latencyMs: 500,
        }}
        readyDocCount={1}
        showPageNumbers
        onRetry={vi.fn()}
      />,
    );
    await expectNoA11yViolations(container);

    rerender(
      <AnswerMessage
        answer={{
          id: "a6",
          phase: "failed",
          markdown: "",
          citations: [],
          errorCode: "SERVICE_BUSY",
        }}
        readyDocCount={1}
        showPageNumbers
        onRetry={vi.fn()}
      />,
    );
    await expectNoA11yViolations(container);
  });
});
