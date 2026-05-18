"use client";

// Vacancy feed page. Two-column layout: filter rail on the left,
// continuous list of vacancies on the right.
//
// Filter changes re-run the search through a debounced `useEffect` (see
// `search` callback below). The AI composer is a separate textarea that
// posts the natural-language query to the backend, which extracts filter
// values and feeds them back into the same state — so AI is just a
// shortcut for filling the form.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { VacancyCard } from "@/components/vacancy-card";
import { Button, Input, Select, Textarea } from "@/components/ui";
import { Stagger } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Vacancy } from "@/lib/types";

export default function VacanciesPage() {
  const t = useTranslations("vacancies");
  const [location, setLocation] = useState("");
  const [stack, setStack] = useState("");
  const [level, setLevel] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [source, setSource] = useState("hh_live");
  const [minSalary, setMinSalary] = useState("");
  const [aiMessage, setAiMessage] = useState("");
  const [aiStatus, setAiStatus] = useState(t("aiStatusInitial"));
  const [loading, setLoading] = useState(false);
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);

  const orderedVacancies = useMemo(
    () => [...vacancies].sort((a, b) => Number(b.is_promoted) - Number(a.is_promoted)),
    [vacancies],
  );

  const search = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.vacancies({
        location,
        stack,
        level,
        source,
        work_mode: workMode,
        min_salary: minSalary ? Number(minSalary) : undefined,
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
    // Re-run search whenever filter inputs change. The transitive setState
    // inside `search` is intentional — this is the "subscribe to filter
    // state" use case the rule's docs explicitly carve out.
    // eslint-disable-next-line react-hooks/set-state-in-effect
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
    <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
      {/* Filter rail — flat, hairline-bordered, no shadows */}
      <aside className="flex flex-col gap-4">
        <section className="rounded border border-border bg-surface p-4">
          {/* h1 stays semantic so a11y + smoke tests can target it via
              getByRole("heading"); the `kicker` class flattens it to a
              low-emphasis editorial label visually. */}
          <h1 className="kicker mb-2">{t("feedTitle")}</h1>
          <p className="text-[13px] leading-[1.5] text-text-secondary">
            {t("feedSubtitle")}
          </p>
        </section>

        <section className="rounded border border-border bg-surface p-4">
          <div className="kicker mb-3">Filters</div>
          <div className="grid gap-2">
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
                { value: "hh_live", label: t("sourceHhLive") },
                { value: "", label: t("sourceAll") },
                { value: "hh", label: t("sourceHh") },
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
            <Button onClick={search} disabled={loading} className="mt-1">
              {loading ? t("buttonSearching") : t("buttonSearch")}
            </Button>
          </div>
        </section>

        <section className="rounded border border-border bg-surface p-4">
          <div className="kicker mb-3">{t("aiCardTitle")}</div>
          <Textarea
            value={aiMessage}
            onChange={setAiMessage}
            placeholder={t("aiPlaceholder")}
            rows={4}
          />
          <Button onClick={runAiComposer} variant="secondary" size="sm" className="mt-2 w-full">
            {t("aiButton")}
          </Button>
          <p
            aria-live="polite"
            className="mt-2 text-[12px] leading-[1.5] text-text-tertiary"
          >
            {aiStatus}
          </p>
        </section>
      </aside>

      {/* Feed — list rhythm, tight gaps, hairline separators inside cards */}
      <section className="min-w-0">
        {orderedVacancies.length === 0 ? (
          <div className="rounded border border-border bg-surface p-6 text-center text-[13px] text-text-tertiary">
            {t("emptyState")}
          </div>
        ) : (
          <Stagger step={0.03} immediate className="flex flex-col">
            {orderedVacancies.map((vacancy) => (
              <VacancyCard key={vacancy.id} vacancy={vacancy} />
            ))}
          </Stagger>
        )}
      </section>
    </div>
  );
}
