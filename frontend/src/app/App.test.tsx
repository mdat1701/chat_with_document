import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { App } from "@app/App";

describe("App", () => {
  it("hiển thị placeholder của route mặc định", () => {
    render(<App />);
    expect(screen.getByTestId("route-placeholder")).toHaveTextContent("SCR-02");
  });
});
