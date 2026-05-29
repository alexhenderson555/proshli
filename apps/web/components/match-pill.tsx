import { useTranslations } from "next-intl";
import { Sparkles } from "lucide-react";
import type { MatchTier } from "@/lib/types";

const TIER_CLASS: Record<MatchTier, string> = {
  strong: "border-accent/40 bg-gradient-to-r from-accent/15 to-indigo-500/10 text-accent shadow-[0_0_12px_rgba(99,102,241,0.15)] font-semibold",
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
        "text-[11px] font-[510] tabular-nums transition-all duration-300 " +
        TIER_CLASS[tier]
      }
    >
      {tier === "strong" && (
        <Sparkles className="h-3 w-3 text-accent animate-pulse" aria-hidden="true" />
      )}
      {percent}% · {t(tier)}
    </span>
  );
}
