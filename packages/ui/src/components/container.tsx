// Page-section wrapper. Relies on the global `.container` utility for
// max-width + horizontal padding so the spacing matches the brand
// design system across breakpoints.

import type { ReactNode } from "react";

import { cn } from "../lib/utils";

export interface ContainerProps {
  children: ReactNode;
  className?: string;
}

export function Container({ children, className }: ContainerProps) {
  return <div className={cn("container", className)}>{children}</div>;
}
