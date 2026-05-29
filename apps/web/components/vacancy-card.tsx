"use client";

// Vacancy list item — Linear-style editorial dense row.
//
// Rendered as `<article>` with a hairline bottom border instead of a
// boxed card. This gives the feed a newspaper-list rhythm instead of a
// pinterest-grid feel: dozens of vacancies scan as a continuous stream
// rather than discrete tiles.
//
// Hover is a colour shift, not a transform — keeps the typography rock
// solid and respects reduced-motion preferences.

import { useLocale, useTranslations } from "next-intl";

import { Badge, Button } from "@/components/ui";
import { MatchPill } from "@/components/match-pill";
import { Link } from "@/i18n/navigation";
import type { Vacancy } from "@/lib/types";
import type { MatchTier } from "@/lib/types";
import { cn } from "@/lib/cn";

export function VacancyCard({ vacancy }: { vacancy: Vacancy }) {
  const t = useTranslations("vacancyCard");
  const locale = useLocale();
  const intlTag = locale === "ru" ? "ru-RU" : "en-US";

  // Salary string — only print the half of the range that actually has a
  // value, then fall back to the "не указана" copy when both are missing.
  const hasSalary = vacancy.salary_from || vacancy.salary_to;
  const salaryText = hasSalary
    ? [
        vacancy.salary_from
          ? `${t("salaryFrom")} ${vacancy.salary_from.toLocaleString(intlTag)}`
          : null,
        vacancy.salary_to
          ? `${t("salaryTo")} ${vacancy.salary_to.toLocaleString(intlTag)}`
          : null,
      ]
        .filter(Boolean)
        .join(" ") + ` ${vacancy.currency}`
    : t("salaryNotSet");

  const published = new Date(vacancy.published_at).toLocaleDateString(intlTag, {
    day: "2-digit",
    month: "short",
  });

  // Source label maps `hh_live` → `HH` so the badge stays tight. Other
  // sources upper-case for visual rhythm with the neutral chip style.
  const sourceLabel =
    vacancy.source === "hh_live" ? "HH" : vacancy.source.toUpperCase();

  const modeLabel = (() => {
    const hay = `${vacancy.location} ${vacancy.description}`.toLowerCase();
    if (hay.includes("remote") || hay.includes("удален")) return t("modeRemote");
    if (hay.includes("hybrid") || hay.includes("гибрид")) return t("modeHybrid");
    if (hay.includes("office") || hay.includes("офис")) return t("modeOffice");
    return null;
  })();

  const isStrongMatch = vacancy.match_score != null && vacancy.match_tier === "strong";

  return (
    <article
      className={cn(
        "group relative border-b border-border px-3 py-4.5 row-hover -mx-2 rounded-md transition-all duration-300",
        isStrongMatch && "border-l-2 border-l-accent/70 pl-3.5 bg-accent/[0.01] hover:bg-accent/[0.02]"
      )}
    >
      {/* Header line: badges + published date, lighter visual weight than title */}
      <div className="flex flex-wrap items-center gap-1.5 text-text-tertiary">
        {vacancy.match_score != null && vacancy.match_tier ? (
          <MatchPill
            score={vacancy.match_score}
            tier={vacancy.match_tier as MatchTier}
          />
        ) : null}
        <Badge text={sourceLabel} />
        {modeLabel ? <Badge text={modeLabel} tone="neutral" /> : null}
        {vacancy.is_promoted ? <Badge text="PROMO" tone="brand" /> : null}
        {!vacancy.is_active ? <Badge text="ARCHIVED" tone="warning" /> : null}
        <span className="ml-auto text-[11px] font-[510] tabular-nums">
          {published}
        </span>
      </div>

      {/* Title row — title + company on first row, salary aligned right */}
      <div className="mt-2 flex items-baseline justify-between gap-4">
        <Link
          href={`/vacancies/${vacancy.id}`}
          className="min-w-0 flex-1 group/title focus-ring"
        >
          <h3 className="truncate text-[15px] font-[580] leading-snug tracking-[-0.01em] text-text-primary group-hover/title:text-accent transition-colors">
            {vacancy.title}
          </h3>
          <p className="mt-0.5 truncate text-[13px] font-[510] text-text-secondary">
            {vacancy.company}
            <span className="mx-1.5 text-text-tertiary">·</span>
            {vacancy.location}
          </p>
        </Link>
        <div className="shrink-0 text-right">
          <div className="text-[13px] font-[510] tabular-nums text-text-primary">
            {salaryText}
          </div>
          <div className="mt-0.5 text-[11px] font-[510] tabular-nums text-text-tertiary">
            {t("applications")}: {vacancy.applications_count}
          </div>
        </div>
      </div>

      {/* Description preview — two lines max, low-emphasis */}
      <p className="mt-2 text-[13px] leading-[1.55] text-text-tertiary line-clamp-2">
        {vacancy.description || t("descriptionEmpty")}
      </p>

      {/* Action row — appears more prominent on hover via group state */}
      <div className="mt-3 flex items-center justify-end gap-1.5 opacity-80 group-hover:opacity-100 transition-opacity">
        {vacancy.external_url ? (
          <a
            href={vacancy.external_url}
            target="_blank"
            rel="noreferrer"
            aria-label={t("openExternal")}
          >
            <Button variant="ghost" size="sm">
              {t("openExternal")}
            </Button>
          </a>
        ) : null}
        <Link href={`/vacancies/${vacancy.id}`}>
          <Button size="sm">{t("open")}</Button>
        </Link>
      </div>
    </article>
  );
}
