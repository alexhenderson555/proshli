// Loading placeholder. Two flavours:
//   * default — soft pulse on the elevated surface
//   * shimmer — diagonal highlight sweep (more "alive", use sparingly)
//
// `aria-hidden` keeps screen readers from announcing pulsing nothings.

import { cn } from "../lib/utils";

export interface SkeletonProps {
  className?: string;
  variant?: "pulse" | "shimmer";
}

export function Skeleton({ className, variant = "pulse" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "rounded",
        variant === "shimmer" ? "shimmer" : "animate-pulse bg-elevated",
        className,
      )}
    />
  );
}
