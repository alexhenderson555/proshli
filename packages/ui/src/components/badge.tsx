// Inline tag. Outlined-only — no solid color washes.
//
// Tones describe semantics:
//   neutral  — generic chip (source, employment type)
//   brand    — promotional / accent-aligned label
//   accent   — alias of `neutral` for backwards compat (no color wash)
//   success  — positive state (remote allowed, hiring active)
//   warning  — caution (closing soon, applications high)
//   danger   — destructive (archived, expired)
//
// All tones share the same elevated bg + border-tint pattern — the
// difference is only the text and border colour. This keeps the badge
// quiet against editorial-dense lists where ten of them might appear
// in a single viewport.

import { cn } from "../lib/utils";

export type BadgeTone =
  | "neutral"
  | "brand"
  | "accent"
  | "success"
  | "warning"
  | "danger";

const badgeTones: Record<BadgeTone, string> = {
  neutral:
    "bg-elevated border border-border text-text-secondary",
  brand:
    "bg-[rgba(99,102,241,0.08)] border border-[rgba(99,102,241,0.25)] text-accent",
  accent:
    "bg-elevated border border-border text-text-secondary",
  success:
    "bg-elevated border border-[rgba(74,222,128,0.22)] text-[#86efac]",
  warning:
    "bg-elevated border border-[rgba(251,191,36,0.22)] text-[#fcd34d]",
  danger:
    "bg-elevated border border-[rgba(239,68,68,0.25)] text-[#fca5a5]",
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
        "inline-flex items-center rounded-sm px-1.5 py-px text-[11px] font-[510] tracking-[0.01em] leading-[1.4]",
        badgeTones[tone],
        className,
      )}
    >
      {text}
    </span>
  );
}
