import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Sheet, SheetContent, SheetTitle } from "./sheet";

describe("Sheet", () => {
  it("opens on the right", () => {
    render(
      <Sheet open>
        <SheetContent side="right">
          <SheetTitle>AI Assistant</SheetTitle>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("AI Assistant")).toBeInTheDocument();
  });
});
