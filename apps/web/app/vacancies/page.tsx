"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { VacancyCard } from "@/components/vacancy-card";
import { Button, Card, Input, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { Vacancy } from "@/lib/types";

export default function VacanciesPage() {
  const [location, setLocation] = useState("");
  const [stack, setStack] = useState("");
  const [level, setLevel] = useState("");
  const [workMode, setWorkMode] = useState("");
  const [source, setSource] = useState("hh_live");
  const [minSalary, setMinSalary] = useState("");
  const [aiMessage, setAiMessage] = useState("");
  const [aiStatus, setAiStatus] = useState("AI композер пока не использовался");
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
      const message = error instanceof Error ? error.message : "Ошибка поиска";
      setAiStatus(`Ошибка поиска: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [level, location, minSalary, source, stack, workMode]);

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
      setAiStatus("Сначала войди в аккаунт, чтобы использовать AI.");
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
      const message = error instanceof Error ? error.message : "AI ошибка";
      setAiStatus(message);
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <div className="flex flex-col gap-4">
        <Card>
          <h1 className="text-xl font-extrabold">Лента вакансий</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            HH-паттерн поиска + кастомная JobSkout-фишка: AI-композер фильтров и приоритет промо-вакансий.
          </p>
          <div className="mt-3 grid gap-2">
            <Input value={location} onChange={setLocation} placeholder="Локация: Москва / Remote" />
            <Input value={stack} onChange={setStack} placeholder="Стек: Python, React, Data" />
            <Select
              value={level}
              onChange={setLevel}
              options={[
                { value: "", label: "Любой уровень" },
                { value: "junior", label: "Junior" },
                { value: "middle", label: "Middle" },
                { value: "senior", label: "Senior" },
              ]}
            />
            <Select
              value={source}
              onChange={setSource}
              options={[
                { value: "hh_live", label: "Только реальные HH" },
                { value: "", label: "Все источники" },
                { value: "hh", label: "HH (из базы)" },
                { value: "manual", label: "Внутренние/ручные" },
              ]}
            />
            <Select
              value={workMode}
              onChange={setWorkMode}
              options={[
                { value: "", label: "Любой формат" },
                { value: "remote", label: "Remote" },
                { value: "hybrid", label: "Hybrid" },
                { value: "office", label: "Office" },
              ]}
            />
            <Input value={minSalary} onChange={setMinSalary} placeholder="Мин. зарплата" />
            <Button onClick={search} disabled={loading}>
              {loading ? "Ищу..." : "Найти вакансии"}
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">AI фильтры</h2>
          <Textarea
            value={aiMessage}
            onChange={setAiMessage}
            placeholder="Например: Ищу middle python удаленно от 250к"
            rows={5}
          />
          <div className="mt-2">
            <Button onClick={runAiComposer}>Разобрать запрос</Button>
          </div>
          <p className="mt-3 text-sm text-[var(--text-muted)]">{aiStatus}</p>
        </Card>
      </div>

      <section className="flex flex-col gap-3">
        {orderedVacancies.length === 0 ? (
          <Card className="text-sm text-[var(--text-muted)]">
            Пусто. Нажми “Найти вакансии”, чтобы загрузить подборку.
          </Card>
        ) : (
          orderedVacancies.map((vacancy) => <VacancyCard key={vacancy.id} vacancy={vacancy} />)
        )}
      </section>
    </div>
  );
}
