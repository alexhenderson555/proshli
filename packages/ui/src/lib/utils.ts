// The canonical `cn(...)` helper that every shadcn/ui-flavoured component
// expects. Wraps `clsx` so callers can pass conditionals and class arrays,
// then runs `tailwind-merge` so conflicting Tailwind classes (e.g.
// `px-2 px-4`) collapse to the last one declared — same behaviour you get
// from a hand-written runtime, but tree-shakable.

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
