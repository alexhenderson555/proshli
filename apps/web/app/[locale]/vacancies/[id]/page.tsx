"use client";

import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Badge, Button, Card } from "@/components/ui";
import { VacancyCard } from "@/components/vacancy-card";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import type { Vacancy } from "@/lib/types";

export default function VacancyDetailsPage() {
  const t = useTranslations("vacancies.detail");
  const locale = useLocale();
  const intlTag = locale === "ru" ? "ru-RU" : "en-US";
  const params = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [related, setRelated] = useState<Vacancy[]>([]);

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

  const salaryLabel = useMemo(() => {
    if (!vacancy) {
      return "—";
    }
    if (!vacancy.salary_from && !vacancy.salary_to) {
      return t("salaryNotSet");
    }
    return `${t("salaryFrom")} ${vacancy.salary_from?.toLocaleString(intlTag) ?? "—"} ${t("salaryTo")} ${
      vacancy.salary_to?.toLocaleString(intlTag) ?? "—"
    } ${vacancy.currency}`;
  }, [vacancy, intlTag, t]);
  const modeLabel = useMemo(() => {
    if (!vacancy) {
      return "";
    }
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
    return t("modeUnknown");
  }, [vacancy, t]);
  const skills = useMemo(() => {
    if (!vacancy?.description) {
      return [];
    }
    const known = [
      "python",
      "sql",
      "postgresql",
      "fastapi",
      "django",
      "flask",
      "kafka",
      "docker",
      "kubernetes",
      "linux",
      "javascript",
      "typescript",
      "react",
      "vue",
      "node",
      "git",
      "ci/cd",
      "airflow",
      "spark",
      "tableau",
      "power bi",
    ];
    const hay = vacancy.description.toLowerCase();
    return known.filter((item) => hay.includes(item)).slice(0, 10);
  }, [vacancy]);
  const quickApplyHref = vacancy?.external_url ?? "";

  if (loading) {
    return <Card>{t("loadingText")}</Card>;
  }

  if (!vacancy) {
    return (
      <Card>
        <p className="text-sm text-[var(--danger)]">{error || t("loadFailed")}</p>
        <Link href="/vacancies" className="mt-2 inline-block">
          <Button variant="secondary">{t("backToFeed")}</Button>
        </Link>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <Card>
        <div className="flex flex-wrap items-center gap-2">
          <Badge text={vacancy.source.toUpperCase()} />
          {vacancy.is_promoted ? <Badge text="PROMO" tone="brand" /> : null}
          <Badge text={vacancy.experience_level.toUpperCase()} tone="success" />
          <Badge text={modeLabel.toUpperCase()} />
        </div>
        <h1 className="mt-3 text-3xl font-extrabold tracking-[-0.01em]">{vacancy.title}</h1>
        <p className="mt-1 text-base font-semibold text-[var(--text-muted)]">
          {vacancy.company} • {vacancy.location}
        </p>
        <div className="mt-4 rounded-2xl border border-[var(--line)] bg-[var(--surface-alt)] p-4">
          <div className="grid gap-2 text-sm text-[var(--text-muted)] md:grid-cols-2">
            <p>
              <span className="font-semibold text-[var(--text)]">{t("salary")}:</span> {salaryLabel}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">{t("applications")}:</span> {vacancy.applications_count}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">{t("published")}:</span>{" "}
              {new Date(vacancy.published_at).toLocaleString(intlTag)}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">{t("employmentType")}:</span> {vacancy.employment_type}
            </p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 whitespace-pre-wrap">{vacancy.description || t("descriptionEmpty")}</p>
        <div className="mt-4 flex gap-2">
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
      </Card>
      <aside className="self-start lg:sticky lg:top-24">
        <Card>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">{t("salary")}</p>
            <p className="mt-1 text-2xl font-extrabold leading-tight text-emerald-800">{salaryLabel}</p>
          </div>
          <h2 className="text-base font-extrabold">{t("keyFacts")}</h2>
          <div className="mt-3 grid gap-2 text-sm text-[var(--text-muted)]">
            <p>
              <span className="font-semibold text-[var(--text)]">{t("salary")}:</span> {salaryLabel}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">{t("format")}:</span> {modeLabel}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">{t("company")}:</span> {vacancy.company}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">{t("location")}:</span> {vacancy.location}
            </p>
          </div>
          <h3 className="mt-4 text-sm font-extrabold">{t("keySkills")}</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {skills.length === 0 ? (
              <span className="text-xs text-[var(--text-muted)]">{t("skillsEmpty")}</span>
            ) : (
              skills.map((item) => <Badge key={item} text={item.toUpperCase()} tone="brand" />)
            )}
          </div>
          <div className="mt-4">
            {vacancy.external_url ? (
              <a href={vacancy.external_url} target="_blank" rel="noreferrer" className="block">
                <Button className="w-full">{t("applyHh")}</Button>
              </a>
            ) : (
              <Button className="w-full">{t("apply")}</Button>
            )}
          </div>
        </Card>
      </aside>

      <section className="grid gap-3 lg:col-span-2">
        <h2 className="text-lg font-bold">{t("similarTitle")}</h2>
        {related.length === 0 ? <Card>{t("similarEmpty")}</Card> : related.map((item) => <VacancyCard key={item.id} vacancy={item} />)}
      </section>
      <div className="fixed inset-x-0 bottom-3 z-40 px-4 lg:hidden">
        {quickApplyHref ? (
          <a href={quickApplyHref} target="_blank" rel="noreferrer" className="mx-auto block w-full max-w-md">
            <Button className="w-full">{t("quickApplyHh")}</Button>
          </a>
        ) : (
          <div className="mx-auto w-full max-w-md">
            <Button className="w-full">{t("quickApply")}</Button>
          </div>
        )}
      </div>
    </div>
  );
}
