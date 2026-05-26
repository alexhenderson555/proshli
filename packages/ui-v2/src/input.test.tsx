import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Input } from "./input";

describe("Input", () => {
  it("renders with placeholder", () => {
    render(<Input placeholder="Enter email" />);
    expect(screen.getByPlaceholderText("Enter email")).toBeInTheDocument();
  });

  it("forwardRef works", () => {
    let ref: HTMLInputElement | null = null;
    render(
      <Input
        ref={(el) => {
          ref = el;
        }}
      />,
    );
    expect(ref).toBeInstanceOf(HTMLInputElement);
  });

  it("accepts type", () => {
    render(<Input type="email" data-testid="x" />);
    expect(screen.getByTestId("x")).toHaveAttribute("type", "email");
  });

  it("error variant adds red border", () => {
    render(<Input error data-testid="x" />);
    expect(screen.getByTestId("x").className).toContain("border-red");
  });
});
