"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { Sparkles, SlidersHorizontal, Cpu, Eye } from "lucide-react";

import { VacancyCard } from "@/components/vacancy-card";
import { Button, Input, Select, Textarea } from "@/components/ui";
import { Stagger } from "@proshli/ui";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Vacancy } from "@/lib/types";
import { HeroBackdrop } from "@/components/hero-backdrop";

export default function VacanciesPage() {
  const t = useTranslations("vacancies");
  const [location, setLocation] = useState("");
  const [stack, setStack] = useState("");
  const [level, setLevel] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [source, setSource] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [aiMessage, setAiMessage] = useState("");
  const [aiStatus, setAiStatus] = useState(t("aiStatusInitial"));
  const [loading, setLoading] = useState(false);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);

  const orderedVacancies = useMemo(
    () => [...vacancies].sort((a, b) => Number(b.is_promoted) - Number(a.is_promoted)),
    [vacancies],
  );

  const hasToken = typeof window !== "undefined" && Boolean(getToken());
  const allMissingScore =
    hasToken &&
    orderedVacancies.length > 0 &&
    orderedVacancies.every((v) => v.match_score == null);

  const search = useCallback(async () => {
    setLoading(true);
    try {
      const token = getToken();
      const data = await api.vacancies({
        location,
        stack,
        level,
        source,
        work_mode: workMode,
        min_salary: minSalary ? Number(minSalary) : undefined,
        include_match: token ? true : undefined,
      });
      setVacancies(data);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorSearch");
      setAiStatus(`${t("errorSearch")}: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [level, location, minSalary, source, stack, workMode, t]);

  useEffect(() => {
    void search();
  }, [search]);

  async function runAiComposer() {
    const token = getToken();
    if (!token) {
      setAiStatus(t("aiNeedsAuth"));
      return;
    }
    try {
      const ai = await api.aiChat(token, aiMessage);
      setAiStatus(ai.message);
      if (ai.extracted_filters) {
        setLocation(ai.extracted_filters.location ?? location);
        setStack(ai.extracted_filters.stack ?? stack);
        setLevel(ai.extracted_filters.level ?? level);
        setWorkMode(ai.extracted_filters.work_mode ?? workMode);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorAi");
      setAiStatus(message);
    }
  }

  return (
    <div className="relative min-h-screen">
      <HeroBackdrop />

      <div className="grid gap-8 py-8 lg:grid-cols-[280px_1fr] relative z-10">
        {/* Filter rail — flat, hairline-bordered, no shadows */}
        <aside className="flex flex-col gap-4">
          <section className="rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-5 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
            <h1 className="text-[12px] font-[600] uppercase tracking-[0.15em] text-accent flex items-center gap-1.5 mb-2">
              <SlidersHorizontal className="h-3.5 w-3.5" />
              {t("feedTitle")}
            </h1>
            <p className="text-[13px] leading-[1.6] text-text-secondary">
              {t("feedSubtitle")}
            </p>
          </section>

          <section className="rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-5 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
            <div className="text-[10px] font-[600] uppercase tracking-[0.12em] text-text-tertiary mb-3">Фильтры</div>
            <div className="grid gap-2.5">
              <Input
                value={location}
                onChange={setLocation}
                placeholder={t("filterLocation")}
              />
              <Input
                value={stack}
                onChange={setStack}
                placeholder={t("filterStack")}
              />
              <Select
                value={level}
                onChange={setLevel}
                options={[
                  { value: "", label: t("filterLevelAny") },
                  { value: "junior", label: t("filterLevelJunior") },
                  { value: "middle", label: t("filterLevelMiddle") },
                  { value: "senior", label: t("filterLevelSenior") },
                ]}
              />
              <Select
                value={source}
                onChange={setSource}
                options={[
                  { value: "", label: t("sourceAll") },
                  { value: "company_sites", label: t("sourceCompanySites") },
                  { value: "habr_career", label: t("sourceHabrCareer") },
                  { value: "telegram", label: t("sourceTelegram") },
                  { value: "hh", label: t("sourceHh") },
                  { value: "hh_live", label: t("sourceHhLive") },
                  { value: "manual", label: t("sourceManual") },
                ]}
              />
              <Select
                value={workMode}
                onChange={setWorkMode}
                options={[
                  { value: "", label: t("workModeAny") },
                  { value: "remote", label: t("workModeRemote") },
                  { value: "hybrid", label: t("workModeHybrid") },
                  { value: "office", label: t("workModeOffice") },
                ]}
              />
              <Input
                value={minSalary}
                onChange={setMinSalary}
                placeholder={t("filterMinSalary")}
              />
              <Button onClick={search} disabled={loading} className="mt-1 bg-accent hover:bg-accent-hover text-white py-2 rounded font-medium shadow-[0_4px_12px_rgba(99,102,241,0.15)]">
                {loading ? t("buttonSearching") : t("buttonSearch")}
              </Button>
            </div>
          </section>

          <section className="rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-5 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
            <div className="text-[10px] font-[600] uppercase tracking-[0.12em] text-text-tertiary flex items-center gap-1.5 mb-3">
              <Cpu className="h-3.5 w-3.5 text-accent" />
              {t("aiCardTitle")}
            </div>
            <Textarea
              value={aiMessage}
              onChange={setAiMessage}
              placeholder={t("aiPlaceholder")}
              rows={4}
              className="bg-elevated/40 border-border focus:border-accent/50 text-[13px] leading-[1.6]"
            />
            <Button onClick={runAiComposer} variant="secondary" size="sm" className="mt-2 w-full border-border/80 hover:border-border-strong text-[12px] py-1.5 font-medium bg-elevated/20">
              {t("aiButton")}
            </Button>
            <p
              aria-live="polite"
              className="mt-2.5 text-[12px] leading-[1.6] text-text-tertiary border-t border-border/30 pt-2"
            >
              {aiStatus}
            </p>
          </section>
        </aside>

        {/* Feed — list rhythm, tight gaps, hairline separators inside cards */}
        <section className="min-w-0">
          {orderedVacancies.length === 0 ? (
            <div className="rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-8 text-center text-[13px] text-text-tertiary shadow-[0_4px_24px_rgba(0,0,0,0.05)]">
              {t("emptyState")}
            </div>
          ) : (
            <>
              {allMissingScore ? (
                <Link
                  href="/seeker"
                  className="mb-4 inline-flex w-fit items-center gap-2 rounded border border-accent/30 bg-accent/10 px-3.5 py-1.5 text-[12px] font-[550] text-accent transition-all duration-200 hover:bg-accent/15 shadow-[0_4px_12px_rgba(99,102,241,0.05)]"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  {t("noResumeCta")} →
                </Link>
              ) : null}
              <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm px-4 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
                <Stagger step={0.03} immediate className="flex flex-col">
                  {orderedVacancies.map((vacancy) => (
                    <VacancyCard key={vacancy.id} vacancy={vacancy} />
                  ))}
                </Stagger>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
