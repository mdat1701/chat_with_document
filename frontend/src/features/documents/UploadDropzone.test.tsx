import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { expectNoA11yViolations } from "@shared/testing/axe";
import { UploadDropzone } from "./UploadDropzone";

describe("UploadDropzone", () => {
  it("hiển thị gợi ý và cho phép chọn tệp", () => {
    render(
      <UploadDropzone
        hintText="PDF có văn bản · tối đa 20 MB"
        onFilesSelected={vi.fn()}
      />,
    );
    expect(screen.getByTestId("upload-dropzone")).toHaveTextContent(
      "PDF có văn bản",
    );
  });

  it("hiển thị tooltip lý do khi bị khóa", () => {
    render(
      <UploadDropzone
        disabled
        disabledReason="Bạn đang ngoại tuyến."
        hintText="PDF có văn bản · tối đa 20 MB"
        onFilesSelected={vi.fn()}
      />,
    );
    expect(screen.getByTestId("upload-dropzone")).toHaveAttribute(
      "aria-disabled",
      "true",
    );
  });

  it("không có vi phạm a11y nghiêm trọng (sẵn sàng và bị khóa)", async () => {
    const { container, rerender } = render(
      <UploadDropzone
        hintText="PDF có văn bản · tối đa 20 MB"
        onFilesSelected={vi.fn()}
      />,
    );
    await expectNoA11yViolations(container);

    rerender(
      <UploadDropzone
        disabled
        disabledReason="Bạn đang ngoại tuyến."
        hintText="PDF có văn bản · tối đa 20 MB"
        onFilesSelected={vi.fn()}
      />,
    );
    await expectNoA11yViolations(container);
  });
});
