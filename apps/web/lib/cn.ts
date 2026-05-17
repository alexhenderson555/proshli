// Re-export of the `cn` helper. Local copy because the workspace import
// from `@otklik/ui` isn't fully wired through Next.js' build pipeline yet
// (transpilePackages config lands in a follow-up). Functionally identical.

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
