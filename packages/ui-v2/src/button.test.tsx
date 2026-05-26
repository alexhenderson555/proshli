import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("renders children as label", () => {
    render(<Button>Apply</Button>);
    expect(screen.getByRole("button", { name: "Apply" })).toBeInTheDocument();
  });

  it("fires onClick on click", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    screen.getByRole("button").click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("applies variant=primary style by default", () => {
    render(<Button>X</Button>);
    expect(screen.getByRole("button").className).toContain("bg-app-dark-accent");
  });

  it("applies variant=ghost style", () => {
    render(<Button variant="ghost">X</Button>);
    expect(screen.getByRole("button").className).toContain("bg-transparent");
  });

  it("disabled blocks click", () => {
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        X
      </Button>,
    );
    screen.getByRole("button").click();
    expect(onClick).not.toHaveBeenCalled();
  });
});
