import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";

describe("Tooltip", () => {
  it("shows content on focus", async () => {
    render(
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger>Button</TooltipTrigger>
          <TooltipContent>Hint</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    // Radix Tooltip's pointerMove path is gated on pointerType !== "touch" and
    // jsdom doesn't synthesise a usable pointer event. Focus calls onOpen()
    // synchronously, which is the keyboard-equivalent path we care about.
    act(() => {
      (screen.getByText("Button") as HTMLElement).focus();
    });
    // Radix renders both the visible content and an aria-describedby span,
    // so query by role=tooltip to assert just the accessible region.
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Hint");
  });
});
