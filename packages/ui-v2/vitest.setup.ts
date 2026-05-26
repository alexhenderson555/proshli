import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// React Testing Library's auto-cleanup is gated on global afterEach (test runners
// that expose it via `globals: true`). We run with `globals: false`, so wire it up
// manually here.
afterEach(() => {
  cleanup();
});

