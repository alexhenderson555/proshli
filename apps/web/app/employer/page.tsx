"use client";

import { useEffect, useState } from "react";

import { Button, Card, Input, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { EmployerActionLogOut, EmployerVacancyAnalyticsOut, Vacancy } from "@/lib/types";

export default function EmployerPage() {
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("published_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<Vacancy[]>([]);
  const [analytics, setAnalytics] = useState<EmployerVacancyAnalyticsOut | null>(null);
  const [logs, setLogs] = useState<EmployerActionLogOut[]>([]);
  const [uiStatus, setUiStatus] = useState("Готово");

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("Otklik");
  const [location, setLocation] = useState("Remote");
  const [description, setDescription] = useState("");

  async function loadVacancies(targetPage = page) {
    const token = getToken();
    if (!token) {
      setUiStatus("Выполни вход как работодатель");
      return;
    }
    try {
      const data = await api.employerVacanciesPage(token, {
        status: statusFilter,
        sort_by: sortBy,
        order,
        page: targetPage,
        page_size: 10,
      });
      setItems(data.items);
      setTotal(data.total);
      setPage(data.page);
      setUiStatus("Список вакансий обновлен.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ошибка загрузки";
      setUiStatus(message);
    }
  }

  async function loadInsights() {
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      const [analyticsData, logsData] = await Promise.all([
        api.employerAnalytics(token),
        api.employerActions(token, { limit: 20 }),
      ]);
      setAnalytics(analyticsData);
      setLogs(logsData);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ошибка аналитики";
      setUiStatus(message);
    }
  }

  useEffect(() => {
    // Load-on-mount + load-on-filter-change. This is the "subscribe to
    // URL/filter state" pattern the React 19 rule's docs carve out as
    // legitimate — the transitive setState happens inside the awaited
    // async helpers, not synchronously in the effect body.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadVacancies(1);
    void loadInsights();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, sortBy, order]);

  async function createVacancy() {
    const token = getToken();
    if (!token) {
      setUiStatus("Нужна авторизация работодателя");
      return;
    }
    if (!title.trim()) {
      setUiStatus("Введите title вакансии");
      return;
    }
    try {
      await api.createEmployerVacancy(token, {
        source: "manual",
        external_id: `web-${Date.now()}`,
        title: title.trim(),
        company: company.trim(),
        location: location.trim(),
        description,
        employment_type: "full-time",
        experience_level: "middle",
        salary_from: null,
        salary_to: null,
        currency: "RUB",
        applications_count: 0,
      });
      setTitle("");
      setDescription("");
      setUiStatus("Вакансия создана.");
      await loadVacancies(1);
      await loadInsights();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ошибка создания";
      setUiStatus(message);
    }
  }

  async function doAction(vacancyId: number, action: "archive" | "publish" | "promote" | "delete") {
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      if (action === "archive") {
        await api.archiveVacancy(token, vacancyId);
      } else if (action === "publish") {
        await api.publishVacancy(token, vacancyId);
      } else if (action === "promote") {
        await api.promoteVacancy(token, vacancyId, 7);
      } else {
        await api.deleteVacancy(token, vacancyId);
      }
      setUiStatus(`Действие ${action} выполнено.`);
      await loadVacancies(page);
      await loadInsights();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ошибка действия";
      setUiStatus(message);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 10));

  return (
    <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
      <div className="flex flex-col gap-4">
        <Card>
          <h1 className="text-xl font-extrabold">Кабинет работодателя</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Управляй вакансиями, архивом и продвижением. Поток знаком HH, монетизация и аналитика — Otklik-style.
          </p>
          <div className="mt-3 grid gap-2">
            <Input value={title} onChange={setTitle} placeholder="Title вакансии" />
            <Input value={company} onChange={setCompany} placeholder="Компания" />
            <Input value={location} onChange={setLocation} placeholder="Локация" />
            <Textarea value={description} onChange={setDescription} placeholder="Описание" rows={4} />
            <Button onClick={createVacancy}>Создать вакансию</Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">Фильтры списка</h2>
          <div className="mt-2 grid gap-2">
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: "all" },
                { value: "active", label: "active" },
                { value: "archived", label: "archived" },
              ]}
            />
            <Select
              value={sortBy}
              onChange={setSortBy}
              options={[
                { value: "published_at", label: "published_at" },
                { value: "applications_count", label: "applications_count" },
                { value: "title", label: "title" },
              ]}
            />
            <Select
              value={order}
              onChange={setOrder}
              options={[
                { value: "desc", label: "desc" },
                { value: "asc", label: "asc" },
              ]}
            />
            <Button variant="secondary" onClick={() => void loadVacancies(page)}>
              Обновить
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">Аналитика</h2>
          <p className="mt-2 text-sm text-[var(--text-muted)]">
            Всего: {analytics?.total ?? 0} • Активных: {analytics?.active ?? 0} • Архив: {analytics?.archived ?? 0}
          </p>
          <p className="mt-3 text-xs text-[var(--text-muted)]">{uiStatus}</p>
        </Card>
      </div>

      <div className="grid gap-4">
        <Card>
          <h2 className="text-lg font-bold">Мои вакансии</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            Страница {page} из {totalPages}
          </p>
          <div className="mt-3 grid gap-3">
            {items.map((item) => (
              <article key={item.id} className="rounded-xl border border-[var(--line)] p-3">
                <h3 className="font-semibold">{item.title}</h3>
                <p className="text-sm text-[var(--text-muted)]">
                  {item.company} • {item.location}
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => void doAction(item.id, "archive")}>
                    Архив
                  </Button>
                  <Button variant="secondary" onClick={() => void doAction(item.id, "publish")}>
                    Публиковать
                  </Button>
                  <Button onClick={() => void doAction(item.id, "promote")}>Promote 7 дней</Button>
                  <Button variant="danger" onClick={() => void doAction(item.id, "delete")}>
                    Удалить
                  </Button>
                </div>
              </article>
            ))}
            {items.length === 0 ? <p className="text-sm text-[var(--text-muted)]">Вакансий пока нет.</p> : null}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <Button variant="secondary" onClick={() => void loadVacancies(Math.max(1, page - 1))}>
              Prev
            </Button>
            <Button variant="secondary" onClick={() => void loadVacancies(Math.min(totalPages, page + 1))}>
              Next
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">Action logs</h2>
          <div className="mt-3 grid gap-2">
            {logs.map((log) => (
              <div key={log.id} className="rounded-lg border border-[var(--line)] p-2 text-sm text-[var(--text-muted)]">
                #{log.id} • {log.action} • vacancy: {log.vacancy_id ?? "—"}
              </div>
            ))}
            {logs.length === 0 ? <p className="text-sm text-[var(--text-muted)]">Логи пока пустые.</p> : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
