"use client";

import { useEffect, useState, Suspense } from "react";
import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { Plus, Archive, ExternalLink, ArrowUpRight, BarChart3, Trash2 } from "lucide-react";

import { Button, Input, Select, Textarea } from "@/components/ui";
import { FadeIn, Stagger } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { EmployerActionLogOut, EmployerVacancyAnalyticsOut, Vacancy } from "@/lib/types";
import { AppShell } from "@/components/app-shell";

function EmployerContent() {
  const t = useTranslations("employer");
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") || "overview") as import("@/components/app-shell").TabKey;

  const [statusFilter, setStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("published_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [items, setItems] = useState<Vacancy[]>([]);
  const [analytics, setAnalytics] = useState<EmployerVacancyAnalyticsOut | null>(null);
  const [logs, setLogs] = useState<EmployerActionLogOut[]>([]);
  const [uiStatus, setUiStatus] = useState(t("statusReady"));
  const [loading, setLoading] = useState(false);

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("Proshli");
  const [location, setLocation] = useState("Remote");
  const [description, setDescription] = useState("");

  const loadData = async (targetPage = page) => {
    const token = getToken();
    if (!token) {
      setUiStatus(t("statusNeedsAuth"));
      return;
    }
    setLoading(true);
    try {
      const [vacanciesData, analyticsData, logsData] = await Promise.all([
        api.employerVacanciesPage(token, {
          status: statusFilter,
          sort_by: sortBy,
          order,
          page: targetPage,
          page_size: 10,
        }),
        api.employerAnalytics(token),
        api.employerActions(token, { limit: 20 }),
      ]);
      setItems(vacanciesData.items);
      setTotal(vacanciesData.total);
      setPage(vacanciesData.page);
      setAnalytics(analyticsData);
      setLogs(logsData);
      setUiStatus(t("statusListUpdated"));
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorLoad");
      setUiStatus(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timeout = setTimeout(() => void loadData(1), 0);
    return () => clearTimeout(timeout);
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
      await loadData(1);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorCreate");
      setUiStatus(message);
    }
  }

  async function doAction(vacancyId: number, action: "archive" | "publish" | "promote" | "delete") {
    const token = getToken();
    if (!token) return;
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
      await loadData(page);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorAction");
      setUiStatus(message);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / 10));

  const stats = [
    { label: "Всего вакансий", value: analytics?.total ?? 0, icon: BarChart3 },
    { label: "Активных", value: analytics?.active ?? 0, icon: ArrowUpRight },
    { label: "В архиве", value: analytics?.archived ?? 0, icon: Archive },
  ];

  return (
    <AppShell activeTab={tab} role="employer">
      <FadeIn y={6} duration={0.3} immediate>
        <header className="mb-6 flex flex-col gap-1.5 border-b border-border/60 pb-5">
          <h1 className="text-[26px] font-[600] leading-tight tracking-[-0.02em] text-white">
            Кабинет работодателя
          </h1>
          <p className="text-[13px] leading-[1.6] text-text-secondary">Управляйте вакансиями и откликами</p>
        </header>
      </FadeIn>

      {tab === "overview" && (
        <div className="flex flex-col gap-6">
          <Stagger step={0.05} immediate className="grid gap-3 sm:grid-cols-3">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  className="flex flex-col gap-1 rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-5 hover:border-accent/40 hover:bg-surface/50 transition-all duration-300 relative group overflow-hidden"
                >
                  <div className="absolute top-4 right-4 text-text-tertiary group-hover:text-accent transition-colors">
                    <Icon className="h-4.5 w-4.5" />
                  </div>
                  <div className="text-[10px] font-[600] uppercase tracking-[0.12em] text-text-tertiary">
                    {stat.label}
                  </div>
                  <div className="text-[26px] font-[600] tabular-nums tracking-[-0.02em] text-white bg-gradient-to-b from-white to-text-secondary bg-clip-text text-transparent mt-1">
                    {stat.value}
                  </div>
                </div>
              );
            })}
          </Stagger>

          <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
            <h2 className="text-[16px] font-[600] text-white flex items-center gap-2 mb-4">
              <Plus className="h-4 w-4 text-accent" /> Создать вакансию
            </h2>
            <div className="grid gap-4 max-w-xl">
              <div className="grid grid-cols-2 gap-4">
                <Input value={title} onChange={setTitle} placeholder={t("titleField")} className="bg-surface/50 border-border/80 text-[13px]" />
                <Input value={company} onChange={setCompany} placeholder={t("companyField")} className="bg-surface/50 border-border/80 text-[13px]" />
              </div>
              <Input value={location} onChange={setLocation} placeholder={t("locationField")} className="bg-surface/50 border-border/80 text-[13px]" />
              <Textarea value={description} onChange={setDescription} placeholder={t("descriptionField")} rows={4} className="bg-surface/50 border-border/80 text-[13px]" />
              <Button onClick={createVacancy} className="w-fit bg-accent hover:bg-accent-hover text-white text-[13px] px-6 shadow-[0_4px_12px_rgba(99,102,241,0.15)]">
                {t("buttonCreate")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {tab === "vacancies" && (
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
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
            <Button variant="secondary" onClick={() => void loadData(page)} className="text-[12px] h-9">
              {t("buttonRefresh")}
            </Button>
          </div>
          {uiStatus !== t("statusReady") && (
            <div className="text-[13px] text-accent px-4 py-2 bg-accent/10 border border-accent/20 rounded-md">
              {uiStatus}
            </div>
          )}

          <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm px-4 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
            <Stagger step={0.03} immediate className="flex flex-col">
              {items.map((item) => (
                <div key={item.id} className="group relative border-b border-border/60 last:border-0 px-2 py-5 flex items-center justify-between gap-4 transition-colors hover:bg-surface/40">
                  <div className="flex flex-col gap-1 min-w-0">
                    <h3 className="truncate text-[15px] font-[550] text-text-primary group-hover:text-accent transition-colors">
                      {item.title}
                    </h3>
                    <p className="truncate text-[13px] text-text-tertiary">
                      {item.company} <span className="mx-1.5 opacity-50">•</span> {item.location}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 opacity-60 group-hover:opacity-100 transition-opacity">
                    {item.is_active ? (
                      <Button variant="secondary" size="sm" onClick={() => void doAction(item.id, "archive")} className="h-7 text-[11px] px-2" title={t("actionArchive")}>
                        <Archive className="h-3 w-3" />
                      </Button>
                    ) : (
                      <Button variant="secondary" size="sm" onClick={() => void doAction(item.id, "publish")} className="h-7 text-[11px] px-2" title={t("actionPublish")}>
                        <ExternalLink className="h-3 w-3" />
                      </Button>
                    )}
                    <Button variant="secondary" size="sm" onClick={() => void doAction(item.id, "promote")} className="h-7 text-[11px] px-2 text-accent" title={t("actionPromote")}>
                      <ArrowUpRight className="h-3 w-3" />
                    </Button>
                    <Button variant="danger" size="sm" onClick={() => void doAction(item.id, "delete")} className="h-7 text-[11px] px-2" title={t("actionDelete")}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              ))}
              {items.length === 0 && !loading && (
                <div className="py-12 text-center text-[13px] text-text-tertiary">
                  {t("emptyVacancies")}
                </div>
              )}
            </Stagger>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <Button variant="secondary" onClick={() => void loadData(Math.max(1, page - 1))} disabled={page === 1} className="text-[12px]">
                {t("buttonPrev")}
              </Button>
              <span className="text-[12px] text-text-tertiary mx-2">{t("pageOf", { page, total: totalPages })}</span>
              <Button variant="secondary" onClick={() => void loadData(Math.min(totalPages, page + 1))} disabled={page === totalPages} className="text-[12px]">
                {t("buttonNext")}
              </Button>
            </div>
          )}
        </div>
      )}

      {tab === "analytics" && (
        <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
          <h2 className="text-[16px] font-[600] text-white mb-4">{t("logsTitle")}</h2>
          <div className="flex flex-col gap-2">
            {logs.map((log) => (
              <div key={log.id} className="rounded border border-border/60 bg-surface/50 p-3 text-[13px] text-text-secondary flex items-center justify-between">
                <span>{t("logLine", { id: log.id, action: log.action, vacancy: log.vacancy_id ?? t("vacancyEmpty") })}</span>
                <span className="text-[11px] text-text-tertiary">{new Date(log.created_at).toLocaleDateString()}</span>
              </div>
            ))}
            {logs.length === 0 && <p className="text-[13px] text-text-tertiary py-4 text-center">{t("logsEmpty")}</p>}
          </div>
        </div>
      )}
      
      {/* For other tabs, just show a placeholder */}
      {(tab === "candidates" || tab === "settings") && (
        <div className="rounded-lg border border-border/80 border-dashed bg-surface/10 p-12 text-center shadow-none">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-surface border border-border mb-3 text-text-tertiary">
            <BarChart3 className="h-4 w-4" />
          </div>
          <h2 className="text-[14px] font-[500] text-text-primary">В разработке</h2>
          <p className="mt-1 text-[13px] text-text-tertiary">Этот раздел появится в следующем спринте.</p>
        </div>
      )}
    </AppShell>
  );
}

export default function EmployerPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-text-tertiary text-sm">Загрузка...</div>}>
      <EmployerContent />
    </Suspense>
  );
}
