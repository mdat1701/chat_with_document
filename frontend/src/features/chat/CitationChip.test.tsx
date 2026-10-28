import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { CitationChip, CitationRef } from "./CitationChip";
import type { CitationVM } from "./types";

vi.mock("@shared/analytics/client", () => ({ track: vi.fn() }));

const citation: CitationVM = {
  index: 1,
  documentId: "d1",
  documentName: "HopDong.pdf",
  pageStart: 12,
  pageEnd: 12,
};

describe("CitationChip", () => {
  it("hiển thị nhãn nguồn với tên tệp và số trang", () => {
    render(
      <CitationChip
        citation={citation}
        highlighted={false}
        showPageNumbers
        onHighlight={vi.fn()}
      />,
    );
    expect(screen.getByTestId("citation-chip")).toHaveTextContent(
      "HopDong.pdf",
    );
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <>
        <CitationChip
          citation={citation}
          highlighted={false}
          showPageNumbers
          onHighlight={vi.fn()}
        />
        <CitationChip
          citation={citation}
          highlighted
          showPageNumbers={false}
          onHighlight={vi.fn()}
        />
      </>,
    );
    await expectNoA11yViolations(container);
  });
});

describe("CitationRef", () => {
  it("hiển thị span thuần khi không có citation khớp", () => {
    render(<CitationRef index={5} highlighted={false} onHighlight={vi.fn()} />);
    expect(screen.getByText("[5]")).toBeInTheDocument();
  });

  it("không có vi phạm a11y nghiêm trọng", async () => {
    const { container } = render(
      <>
        <CitationRef
          index={1}
          citation={citation}
          highlighted={false}
          onHighlight={vi.fn()}
        />
        <CitationRef index={5} highlighted={false} onHighlight={vi.fn()} />
      </>,
    );
    await expectNoA11yViolations(container);
  });
});
