"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";

import { VacancyCard } from "@/components/vacancy-card";
import { Button, Card, Input, Select, Textarea } from "@/components/ui";
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
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <div className="flex flex-col gap-4">
        <Card>
          <h1 className="text-xl font-extrabold">{t("feedTitle")}</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{t("feedSubtitle")}</p>
          <div className="mt-3 grid gap-2">
            <Input value={location} onChange={setLocation} placeholder={t("filterLocation")} />
            <Input value={stack} onChange={setStack} placeholder={t("filterStack")} />
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
            <Input value={minSalary} onChange={setMinSalary} placeholder={t("filterMinSalary")} />
            <Button onClick={search} disabled={loading}>
              {loading ? t("buttonSearching") : t("buttonSearch")}
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">{t("aiCardTitle")}</h2>
          <Textarea
            value={aiMessage}
            onChange={setAiMessage}
            placeholder={t("aiPlaceholder")}
            rows={5}
          />
          <div className="mt-2">
            <Button onClick={runAiComposer}>{t("aiButton")}</Button>
          </div>
          <p className="mt-3 text-sm text-[var(--text-muted)]">{aiStatus}</p>
        </Card>
      </div>

      <section className="flex flex-col gap-3">
        {orderedVacancies.length === 0 ? (
          <Card className="text-sm text-[var(--text-muted)]">{t("emptyState")}</Card>
        ) : (
          orderedVacancies.map((vacancy) => <VacancyCard key={vacancy.id} vacancy={vacancy} />)
        )}
      </section>
    </div>
  );
}
