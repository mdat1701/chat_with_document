import { describe, expect, it } from "vitest";
import { validateFiles } from "./files";

const CONFIG = { max_file_size_bytes: 1024, max_documents: 10 };

function pdfFile(name = "doc.pdf", body = "%PDF-1.4\n...") {
  return new File([body], name, { type: "application/pdf" });
}

describe("validateFiles", () => {
  it("accepts a real PDF file", async () => {
    const [result] = await validateFiles([pdfFile()], CONFIG, 0);
    expect(result.ok).toBe(true);
  });

  it("rejects a PNG renamed to .pdf (fails magic-byte check)", async () => {
    const fakePdf = new File(
      [new Uint8Array([0x89, 0x50, 0x4e, 0x47])],
      "image.pdf",
      { type: "application/pdf" },
    );
    const [result] = await validateFiles([fakePdf], CONFIG, 0);
    expect(result.ok).toBe(false);
    expect(result.reasonCode).toBe("FILE_NOT_PDF");
  });

  it("rejects a file whose name/type is not pdf before reading bytes", async () => {
    const txtFile = new File(["hello"], "notes.txt", { type: "text/plain" });
    const [result] = await validateFiles([txtFile], CONFIG, 0);
    expect(result.ok).toBe(false);
    expect(result.reasonCode).toBe("FILE_NOT_PDF");
  });

  it("still enforces size limit after the signature check passes", async () => {
    const big = pdfFile("big.pdf", "%PDF-" + "a".repeat(2000));
    const [result] = await validateFiles([big], CONFIG, 0);
    expect(result.ok).toBe(false);
    expect(result.reasonCode).toBe("FILE_TOO_LARGE");
  });

  it("still enforces quota after the signature check passes", async () => {
    const [result] = await validateFiles([pdfFile()], CONFIG, 10);
    expect(result.ok).toBe(false);
    expect(result.reasonCode).toBe("QUOTA_EXCEEDED");
  });
});
