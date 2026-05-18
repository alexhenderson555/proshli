// Inline status pill. Six tones cover the in-app statuses:
// neutral / brand / accent for informational use; success / warning /
// danger for state cues. Each tone keeps its own token references so
// dark and oled themes pick up the right contrast pair.

import { cn } from "../lib/utils";

export type BadgeTone =
  | "neutral"
  | "brand"
  | "accent"
  | "success"
  | "warning"
  | "danger";

const badgeTones: Record<BadgeTone, string> = {
  neutral: "bg-muted text-muted-foreground",
  brand: "bg-primary/10 text-primary",
  accent: "bg-accent/10 text-accent",
  success: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  warning: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  danger: "bg-destructive/10 text-destructive",
};

export interface BadgeProps {
  text: string;
  tone?: BadgeTone;
  className?: string;
}

export function Badge({ text, tone = "neutral", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        badgeTones[tone],
        className,
      )}
    >
      {text}
    </span>
  );
}
