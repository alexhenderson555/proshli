"use client";

// Match-score pill. Renders `{percent}% · {label}` with tier-coloured
// background. Strong = accent (loud — this is the moment of conversion);
// decent/stretch/longshot fade progressively quieter. We deliberately
// don't shout about bad matches — they're useful as filter signal but
// shouldn't compete with the title.

import { useTranslations } from "next-intl";
import type { MatchTier } from "@/lib/types";

const TIER_CLASS: Record<MatchTier, string> = {
  strong: "border-accent/30 bg-accent/10 text-accent",
  decent: "border-border bg-elevated text-text-primary",
  stretch: "border-border bg-elevated text-text-secondary",
  longshot: "border-border bg-elevated text-text-tertiary",
};

export function MatchPill({
  score,
  tier,
}: {
  score: number;
  tier: MatchTier;
}) {
  const t = useTranslations("matchScore");
  const percent = Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <span
      data-tier={tier}
      className={
        "inline-flex items-center gap-1 rounded border px-1.5 py-0.5 " +
        "text-[11px] font-[510] tabular-nums " +
        TIER_CLASS[tier]
      }
    >
      {percent}% · {t(tier)}
    </span>
  );
}
