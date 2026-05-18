// Animated placeholder for loading states. `aria-hidden` keeps screen
// readers from announcing pulsing nothings.

import { cn } from "../lib/utils";

export interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn("animate-pulse rounded-md bg-muted", className)}
    />
  );
}
