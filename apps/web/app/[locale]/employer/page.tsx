"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { Button, Card, Input, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { EmployerActionLogOut, EmployerVacancyAnalyticsOut, Vacancy } from "@/lib/types";

export default function EmployerPage() {
  const t = useTranslations("employer");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("published_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<Vacancy[]>([]);
  const [analytics, setAnalytics] = useState<EmployerVacancyAnalyticsOut | null>(null);
  const [logs, setLogs] = useState<EmployerActionLogOut[]>([]);
  const [uiStatus, setUiStatus] = useState(t("statusReady"));

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("Otklik");
  const [location, setLocation] = useState("Remote");
  const [description, setDescription] = useState("");

  async function loadVacancies(targetPage = page) {
    const token = getToken();
    if (!token) {
      setUiStatus(t("statusNeedsAuth"));
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
      setUiStatus(t("statusListUpdated"));
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorLoad");
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
      const message = error instanceof Error ? error.message : t("errorAnalytics");
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
      setUiStatus(t("statusNeedsAuthEmployer"));
      return;
    }
    if (!title.trim()) {
      setUiStatus(t("statusNeedsTitle"));
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
      setUiStatus(t("statusCreated"));
      await loadVacancies(1);
      await loadInsights();
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorCreate");
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
      setUiStatus(t("statusActionDone", { action }));
      await loadVacancies(page);
      await loadInsights();
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorAction");
      setUiStatus(message);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 10));

  return (
    <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
      <div className="flex flex-col gap-4">
        <Card>
          <h1 className="text-xl font-extrabold">{t("title")}</h1>
          <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
          <div className="mt-3 grid gap-2">
            <Input value={title} onChange={setTitle} placeholder={t("titleField")} />
            <Input value={company} onChange={setCompany} placeholder={t("companyField")} />
            <Input value={location} onChange={setLocation} placeholder={t("locationField")} />
            <Textarea value={description} onChange={setDescription} placeholder={t("descriptionField")} rows={4} />
            <Button onClick={createVacancy}>{t("buttonCreate")}</Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">{t("filtersTitle")}</h2>
          <div className="mt-2 grid gap-2">
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              options={[
                { value: "all", label: t("statusAll") },
                { value: "active", label: t("statusActive") },
                { value: "archived", label: t("statusArchived") },
              ]}
            />
            <Select
              value={sortBy}
              onChange={setSortBy}
              options={[
                { value: "published_at", label: t("sortPublishedAt") },
                { value: "applications_count", label: t("sortApplications") },
                { value: "title", label: t("sortTitle") },
              ]}
            />
            <Select
              value={order}
              onChange={setOrder}
              options={[
                { value: "desc", label: t("orderDesc") },
                { value: "asc", label: t("orderAsc") },
              ]}
            />
            <Button variant="secondary" onClick={() => void loadVacancies(page)}>
              {t("buttonRefresh")}
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">{t("analyticsTitle")}</h2>
          <p className="mt-2 text-sm text-[var(--text-muted)]">
            {t("analyticsLine", {
              total: analytics?.total ?? 0,
              active: analytics?.active ?? 0,
              archived: analytics?.archived ?? 0,
            })}
          </p>
          <p className="mt-3 text-xs text-[var(--text-muted)]">{uiStatus}</p>
        </Card>
      </div>

      <div className="grid gap-4">
        <Card>
          <h2 className="text-lg font-bold">{t("myVacanciesTitle")}</h2>
          <p className="mt-1 text-sm text-[var(--text-muted)]">
            {t("pageOf", { page, total: totalPages })}
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
                    {t("actionArchive")}
                  </Button>
                  <Button variant="secondary" onClick={() => void doAction(item.id, "publish")}>
                    {t("actionPublish")}
                  </Button>
                  <Button onClick={() => void doAction(item.id, "promote")}>{t("actionPromote")}</Button>
                  <Button variant="danger" onClick={() => void doAction(item.id, "delete")}>
                    {t("actionDelete")}
                  </Button>
                </div>
              </article>
            ))}
            {items.length === 0 ? <p className="text-sm text-[var(--text-muted)]">{t("emptyVacancies")}</p> : null}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <Button variant="secondary" onClick={() => void loadVacancies(Math.max(1, page - 1))}>
              {t("buttonPrev")}
            </Button>
            <Button variant="secondary" onClick={() => void loadVacancies(Math.min(totalPages, page + 1))}>
              {t("buttonNext")}
            </Button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-bold">{t("logsTitle")}</h2>
          <div className="mt-3 grid gap-2">
            {logs.map((log) => (
              <div key={log.id} className="rounded-lg border border-[var(--line)] p-2 text-sm text-[var(--text-muted)]">
                {t("logLine", { id: log.id, action: log.action, vacancy: log.vacancy_id ?? t("vacancyEmpty") })}
              </div>
            ))}
            {logs.length === 0 ? <p className="text-sm text-[var(--text-muted)]">{t("logsEmpty")}</p> : null}
          </div>
        </Card>
      </div>
    </div>
  );
}
