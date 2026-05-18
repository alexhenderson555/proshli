"use client";

// Compact card used in the vacancy feed and similar-list. Translations
// come from `vacancyCard.*`; the keyword-detection (`remote`/`удален`) is
// a content-detection heuristic on the upstream description and stays
// hard-coded so it works regardless of UI locale.

import { useLocale, useTranslations } from "next-intl";

import { Badge, Button } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import type { Vacancy } from "@/lib/types";

export function VacancyCard({ vacancy }: { vacancy: Vacancy }) {
  const t = useTranslations("vacancyCard");
  const locale = useLocale();
  const intlTag = locale === "ru" ? "ru-RU" : "en-US";

  const salary =
    vacancy.salary_from || vacancy.salary_to
      ? `${t("salaryFrom")} ${vacancy.salary_from?.toLocaleString(intlTag) ?? "—"} ${t(
          "salaryTo",
        )} ${vacancy.salary_to?.toLocaleString(intlTag) ?? "—"} ${vacancy.currency}`
      : t("salaryNotSet");
  const published = new Date(vacancy.published_at).toLocaleDateString(intlTag, {
    day: "2-digit",
    month: "long",
  });
  const sourceLabel = vacancy.source === "hh_live" ? "HH" : vacancy.source.toUpperCase();
  const modeLabel = (() => {
    const hay = `${vacancy.location} ${vacancy.description}`.toLowerCase();
    if (hay.includes("remote") || hay.includes("удален")) {
      return t("modeRemote");
    }
    if (hay.includes("hybrid") || hay.includes("гибрид")) {
      return t("modeHybrid");
    }
    if (hay.includes("office") || hay.includes("офис")) {
      return t("modeOffice");
    }
    return null;
  })();

  return (
    <article className="panel p-5 transition hover:-translate-y-0.5 hover:shadow-[0_14px_40px_rgba(16,24,40,0.12)]">
      <div className="flex flex-wrap items-center gap-2">
        <Badge text={sourceLabel} />
        {modeLabel ? <Badge text={modeLabel} tone="success" /> : null}
        {vacancy.is_promoted ? <Badge text="PROMO" tone="brand" /> : null}
        {!vacancy.is_active ? <Badge text="ARCHIVED" tone="warning" /> : null}
      </div>
      <h3 className="mt-3 text-[22px] leading-tight font-extrabold tracking-[-0.01em]">{vacancy.title}</h3>
      <p className="mt-1 text-[15px] font-semibold text-[var(--text-muted)]">
        {vacancy.company} • {vacancy.location}
      </p>
      <p className="mt-3 rounded-xl bg-[var(--surface-alt)] px-3 py-2 text-[13px] text-[var(--text-muted)] line-clamp-3">
        {vacancy.description || t("descriptionEmpty")}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
        <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-700">{salary}</span>
        <span>•</span>
        <span>
          {t("applications")}: {vacancy.applications_count}
        </span>
      </div>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-xs text-[var(--text-muted)]">
          {t("published")}: {published}
        </span>
        <div className="flex items-center gap-2">
          {vacancy.external_url ? (
            <a href={vacancy.external_url} target="_blank" rel="noreferrer">
              <Button variant="ghost">{t("openExternal")}</Button>
            </a>
          ) : null}
          <Link href={`/vacancies/${vacancy.id}`}>
            <Button>{t("open")}</Button>
          </Link>
        </div>
      </div>
    </article>
  );
}
