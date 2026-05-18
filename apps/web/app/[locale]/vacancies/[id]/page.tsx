"use client";

// Vacancy detail page. Two columns on desktop (main content + sticky
// aside with salary + key facts), single column on mobile with a fixed
// bottom CTA bar so the "Apply" button is always reachable.

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Badge, Button } from "@/components/ui";
import { MatchPill } from "@/components/match-pill";
import { VacancyCard } from "@/components/vacancy-card";
import { FadeIn } from "@proshli/ui";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { MatchScoreOut, Vacancy } from "@/lib/types";

export default function VacancyDetailsPage() {
  const t = useTranslations("vacancies.detail");
  const locale = useLocale();
  const intlTag = locale === "ru" ? "ru-RU" : "en-US";
  const params = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [related, setRelated] = useState<Vacancy[]>([]);
  const [match, setMatch] = useState<MatchScoreOut | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      const idNum = Number(params.id);
      if (!Number.isFinite(idNum) || idNum <= 0) {
        setError(t("invalidId"));
        setVacancy(null);
        setRelated([]);
        setLoading(false);
        return;
      }
      try {
        // Detail first — one O(1) lookup instead of fetching the full list.
        const current = await api.vacancy(idNum);
        setVacancy(current);
        // "Similar" still pulls the list, but only because there is no
        // /vacancies/{id}/similar endpoint yet. When that lands we'll switch.
        const all = await api.vacancies({}).catch(() => [] as Vacancy[]);
        setRelated(
          all
            .filter((item) => item.id !== current.id)
            .filter(
              (item) =>
                item.experience_level === current.experience_level ||
                item.location === current.location,
            )
            .slice(0, 3),
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : t("loadFailed");
        // 404 from the API arrives as a thrown Error with the FastAPI detail.
        if (message.toLowerCase().includes("not found") || message.includes("404")) {
          setError(t("notFound"));
        } else {
          setError(message);
        }
        setVacancy(null);
        setRelated([]);
      } finally {
        setLoading(false);
      }
    }
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  useEffect(() => {
    const token = getToken();
    if (!token || !vacancy) return;
    let cancelled = false;
    api.matchScore(token, vacancy.id)
      .then((res) => { if (!cancelled) setMatch(res); })
      .catch(() => { /* swallow — 401/404 just means we render nothing */ });
    return () => { cancelled = true; };
  }, [vacancy]);

  const salaryLabel = useMemo(() => {
    if (!vacancy) return "—";
    if (!vacancy.salary_from && !vacancy.salary_to) return t("salaryNotSet");
    return [
      vacancy.salary_from
        ? `${t("salaryFrom")} ${vacancy.salary_from.toLocaleString(intlTag)}`
        : null,
      vacancy.salary_to
        ? `${t("salaryTo")} ${vacancy.salary_to.toLocaleString(intlTag)}`
        : null,
    ]
      .filter(Boolean)
      .join(" ") + ` ${vacancy.currency}`;
  }, [vacancy, intlTag, t]);

  const modeLabel = useMemo(() => {
    if (!vacancy) return "";
    const hay = `${vacancy.location} ${vacancy.description}`.toLowerCase();
    if (hay.includes("remote") || hay.includes("удален")) return t("modeRemote");
    if (hay.includes("hybrid") || hay.includes("гибрид")) return t("modeHybrid");
    if (hay.includes("office") || hay.includes("офис")) return t("modeOffice");
    return t("modeUnknown");
  }, [vacancy, t]);

  const skills = useMemo(() => {
    if (!vacancy?.description) return [];
    const known = [
      "python", "sql", "postgresql", "fastapi", "django", "flask",
      "kafka", "docker", "kubernetes", "linux", "javascript", "typescript",
      "react", "vue", "node", "git", "ci/cd", "airflow", "spark",
      "tableau", "power bi",
    ];
    const hay = vacancy.description.toLowerCase();
    return known.filter((item) => hay.includes(item)).slice(0, 10);
  }, [vacancy]);

  const quickApplyHref = vacancy?.external_url ?? "";

  if (loading) {
    return (
      <div className="rounded border border-border bg-surface p-6 text-[13px] text-text-tertiary">
        {t("loadingText")}
      </div>
    );
  }

  if (!vacancy) {
    return (
      <div className="rounded border border-border bg-surface p-6">
        <p className="text-[13px] text-[var(--danger)]">{error || t("loadFailed")}</p>
        <Link href="/vacancies" className="mt-3 inline-block">
          <Button variant="secondary" size="sm">
            {t("backToFeed")}
          </Button>
        </Link>
      </div>
    );
  }

  const published = new Date(vacancy.published_at).toLocaleString(intlTag, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px] pb-24 lg:pb-0">
      <FadeIn y={6} duration={0.35} immediate>
        <article className="rounded border border-border bg-surface p-6">
          {/* Header chips */}
          <div className="flex flex-wrap items-center gap-1.5">
            <Badge text={vacancy.source.toUpperCase()} />
            {vacancy.is_promoted ? <Badge text="PROMO" tone="brand" /> : null}
            <Badge text={vacancy.experience_level.toUpperCase()} />
            <Badge text={modeLabel.toUpperCase()} />
            {!vacancy.is_active ? <Badge text="ARCHIVED" tone="warning" /> : null}
          </div>

          <h1 className="mt-4 text-[28px] font-[580] leading-[1.15] tracking-[-0.02em] text-text-primary">
            {vacancy.title}
          </h1>
          <p className="mt-1.5 text-[14px] font-[510] text-text-secondary">
            {vacancy.company}
            <span className="mx-2 text-text-tertiary">·</span>
            {vacancy.location}
          </p>

          {/* Meta grid */}
          <dl className="mt-5 grid gap-x-6 gap-y-3 rounded border border-border bg-elevated p-4 sm:grid-cols-2">
            {[
              [t("salary"), salaryLabel],
              [t("applications"), String(vacancy.applications_count)],
              [t("published"), published],
              [t("employmentType"), vacancy.employment_type],
            ].map(([label, value]) => (
              <div key={label} className="flex flex-col gap-0.5">
                <dt className="text-[10px] font-[510] uppercase tracking-[0.1em] text-text-tertiary">
                  {label}
                </dt>
                <dd className="text-[13px] font-[510] tabular-nums text-text-primary">
                  {value}
                </dd>
              </div>
            ))}
          </dl>

          {/* Description */}
          <p className="mt-6 text-[14px] leading-[1.65] text-text-secondary whitespace-pre-wrap">
            {vacancy.description || t("descriptionEmpty")}
          </p>

          {/* Bottom actions (desktop only — mobile uses sticky bar) */}
          <div className="mt-6 hidden lg:flex items-center gap-2">
            {vacancy.external_url ? (
              <a href={vacancy.external_url} target="_blank" rel="noreferrer">
                <Button>{t("applyHh")}</Button>
              </a>
            ) : (
              <Button>{t("apply")}</Button>
            )}
            <Link href="/vacancies">
              <Button variant="secondary">{t("backToFeed")}</Button>
            </Link>
          </div>
        </article>
      </FadeIn>

      {/* Sticky aside — salary callout + key facts + skills */}
      <aside className="self-start lg:sticky lg:top-20 flex flex-col gap-3">
        {match ? (
          <section className="rounded border border-border bg-surface p-3">
            <div className="kicker mb-1.5">{t("matchTitle")}</div>
            <MatchPill score={match.score} tier={match.tier} />
          </section>
        ) : null}

        <section className="rounded border border-border-strong bg-elevated p-4">
          <div className="kicker">{t("salary")}</div>
          <p className="mt-1 text-[22px] font-[580] tabular-nums leading-tight text-text-primary">
            {salaryLabel}
          </p>
        </section>

        <section className="rounded border border-border bg-surface p-4">
          <div className="kicker mb-3">{t("keyFacts")}</div>
          <dl className="grid gap-2.5 text-[13px]">
            {[
              [t("format"), modeLabel],
              [t("company"), vacancy.company],
              [t("location"), vacancy.location],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex items-baseline justify-between gap-3"
              >
                <dt className="text-text-tertiary">{label}</dt>
                <dd className="text-text-primary text-right truncate">{value}</dd>
              </div>
            ))}
          </dl>

          <div className="mt-4 border-t border-border pt-3">
            <div className="kicker mb-2">{t("keySkills")}</div>
            <div className="flex flex-wrap gap-1">
              {skills.length === 0 ? (
                <span className="text-[12px] text-text-tertiary">
                  {t("skillsEmpty")}
                </span>
              ) : (
                skills.map((item) => (
                  <Badge key={item} text={item.toUpperCase()} />
                ))
              )}
            </div>
          </div>

          <div className="mt-4">
            {vacancy.external_url ? (
              <a
                href={vacancy.external_url}
                target="_blank"
                rel="noreferrer"
                className="block"
              >
                <Button className="w-full">{t("applyHh")}</Button>
              </a>
            ) : (
              <Button className="w-full">{t("apply")}</Button>
            )}
          </div>
        </section>
      </aside>

      {/* Similar vacancies — spans both columns */}
      <section className="lg:col-span-2">
        <div className="kicker mb-3">{t("similarTitle")}</div>
        {related.length === 0 ? (
          <div className="rounded border border-border bg-surface p-4 text-[13px] text-text-tertiary">
            {t("similarEmpty")}
          </div>
        ) : (
          <div className="rounded border border-border bg-surface px-4">
            {related.map((item) => (
              <VacancyCard key={item.id} vacancy={item} />
            ))}
          </div>
        )}
      </section>

      {/* Mobile sticky action bar — bottom of viewport, safe-area aware */}
      <div
        className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface/95 backdrop-blur-md px-4 py-3 lg:hidden"
        style={{ paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom))" }}
      >
        {quickApplyHref ? (
          <a
            href={quickApplyHref}
            target="_blank"
            rel="noreferrer"
            className="block"
          >
            <Button className="w-full" size="lg">
              {t("quickApplyHh")}
            </Button>
          </a>
        ) : (
          <Button className="w-full" size="lg">
            {t("quickApply")}
          </Button>
        )}
      </div>
    </div>
  );
}
