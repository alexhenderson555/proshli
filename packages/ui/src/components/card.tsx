// Standard panel surface. Uses the `.panel` utility class declared in
// the global stylesheet so border, radius, and shadow are token-driven
// and re-skin across themes automatically.

import type { ReactNode } from "react";

import { cn } from "../lib/utils";

export interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <section className={cn("panel p-4", className)}>{children}</section>;
}
