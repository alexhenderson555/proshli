"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { Badge, Button, Card } from "@/components/ui";
import { VacancyCard } from "@/components/vacancy-card";
import { api } from "@/lib/api";
import type { Vacancy } from "@/lib/types";

export default function VacancyDetailsPage() {
  const params = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [related, setRelated] = useState<Vacancy[]>([]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const all = await api.vacancies({});
        const idNum = Number(params.id);
        const current = all.find((item) => item.id === idNum) ?? null;
        if (!current) {
          setError("Вакансия не найдена");
          setVacancy(null);
          setRelated([]);
          return;
        }
        setVacancy(current);
        setRelated(
          all
            .filter((item) => item.id !== current.id)
            .filter((item) => item.experience_level === current.experience_level || item.location === current.location)
            .slice(0, 3),
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : "Ошибка загрузки";
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [params.id]);

  const salaryLabel = useMemo(() => {
    if (!vacancy) {
      return "—";
    }
    if (!vacancy.salary_from && !vacancy.salary_to) {
      return "Не указана";
    }
    return `от ${vacancy.salary_from?.toLocaleString("ru-RU") ?? "—"} до ${
      vacancy.salary_to?.toLocaleString("ru-RU") ?? "—"
    } ${vacancy.currency}`;
  }, [vacancy]);
  const modeLabel = useMemo(() => {
    if (!vacancy) {
      return "";
    }
    const hay = `${vacancy.location} ${vacancy.description}`.toLowerCase();
    if (hay.includes("remote") || hay.includes("удален")) {
      return "Удаленно";
    }
    if (hay.includes("hybrid") || hay.includes("гибрид")) {
      return "Гибрид";
    }
    if (hay.includes("office") || hay.includes("офис")) {
      return "Офис";
    }
    return "Не указан";
  }, [vacancy]);
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
    return <Card>Загрузка...</Card>;
  }

  if (!vacancy) {
    return (
      <Card>
        <p className="text-sm text-[var(--danger)]">{error || "Не удалось загрузить вакансию"}</p>
        <Link href="/vacancies" className="mt-2 inline-block">
          <Button variant="secondary">Назад в ленту</Button>
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
              <span className="font-semibold text-[var(--text)]">Зарплата:</span> {salaryLabel}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">Откликов:</span> {vacancy.applications_count}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">Опубликовано:</span>{" "}
              {new Date(vacancy.published_at).toLocaleString("ru-RU")}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">Тип занятости:</span> {vacancy.employment_type}
            </p>
          </div>
        </div>
        <p className="mt-4 text-sm leading-7 whitespace-pre-wrap">{vacancy.description || "Описание не указано"}</p>
        <div className="mt-4 flex gap-2">
          {vacancy.external_url ? (
            <a href={vacancy.external_url} target="_blank" rel="noreferrer">
              <Button>Откликнуться на HH</Button>
            </a>
          ) : (
            <Button>Откликнуться</Button>
          )}
          <Link href="/vacancies">
            <Button variant="secondary">К ленте</Button>
          </Link>
        </div>
      </Card>
      <aside className="self-start lg:sticky lg:top-24">
        <Card>
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Зарплата</p>
            <p className="mt-1 text-2xl font-extrabold leading-tight text-emerald-800">{salaryLabel}</p>
          </div>
          <h2 className="text-base font-extrabold">Ключевые параметры</h2>
          <div className="mt-3 grid gap-2 text-sm text-[var(--text-muted)]">
            <p>
              <span className="font-semibold text-[var(--text)]">Зарплата:</span> {salaryLabel}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">Формат:</span> {modeLabel}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">Компания:</span> {vacancy.company}
            </p>
            <p>
              <span className="font-semibold text-[var(--text)]">Локация:</span> {vacancy.location}
            </p>
          </div>
          <h3 className="mt-4 text-sm font-extrabold">Ключевые навыки</h3>
          <div className="mt-2 flex flex-wrap gap-2">
            {skills.length === 0 ? (
              <span className="text-xs text-[var(--text-muted)]">Не удалось извлечь автоматически</span>
            ) : (
              skills.map((item) => <Badge key={item} text={item.toUpperCase()} tone="brand" />)
            )}
          </div>
          <div className="mt-4">
            {vacancy.external_url ? (
              <a href={vacancy.external_url} target="_blank" rel="noreferrer" className="block">
                <Button className="w-full">Откликнуться на HH</Button>
              </a>
            ) : (
              <Button className="w-full">Откликнуться</Button>
            )}
          </div>
        </Card>
      </aside>

      <section className="grid gap-3 lg:col-span-2">
        <h2 className="text-lg font-bold">Похожие вакансии</h2>
        {related.length === 0 ? <Card>Пока нет похожих вакансий.</Card> : related.map((item) => <VacancyCard key={item.id} vacancy={item} />)}
      </section>
      <div className="fixed inset-x-0 bottom-3 z-40 px-4 lg:hidden">
        {quickApplyHref ? (
          <a href={quickApplyHref} target="_blank" rel="noreferrer" className="mx-auto block w-full max-w-md">
            <Button className="w-full">Быстрый отклик на HH</Button>
          </a>
        ) : (
          <div className="mx-auto w-full max-w-md">
            <Button className="w-full">Быстрый отклик</Button>
          </div>
        )}
      </div>
    </div>
  );
}
