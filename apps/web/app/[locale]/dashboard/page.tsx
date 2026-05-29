"use client";

import { useEffect, useState } from "react";
import { LayoutGrid, Bookmark, ClipboardList, Settings as SettingsIcon, ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui";
import { KanbanBoard } from "@/components/kanban-board";
import { SavedList } from "@/components/saved-list";
import { VacancyCard } from "@/components/vacancy-card";
import { FadeIn, Stagger } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type {
  ApplicationCountsOut,
  ApplicationOut,
  SeekerProfileOut,
  Vacancy,
} from "@/lib/types";
import { AppShell } from "@/components/app-shell";
import { HeroBackdrop } from "@/components/hero-backdrop";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

function DashboardContent() {
  const t = useTranslations("dashboard");
  const searchParams = useSearchParams();
  const tab = (searchParams.get("tab") || "overview") as import("@/components/app-shell").TabKey;
  const [token, setTokenValue] = useState<string | null>(null);
  const [profile, setProfile] = useState<SeekerProfileOut | null>(null);
  const [recent, setRecent] = useState<Vacancy[]>([]);
  const [applications, setApplications] = useState<ApplicationOut[]>([]);
  const [counts, setCounts] = useState<ApplicationCountsOut | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setTokenValue(getToken()), 0);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [p, v, apps, cnt] = await Promise.all([
          api.seekerProfile(token!).catch(() => null),
          api.vacancies({}).catch(() => [] as Vacancy[]),
          api.listApplications(token!).catch(() => [] as ApplicationOut[]),
          api.applicationCounts(token!).catch(
            () =>
              ({
                saved: 0,
                applied: 0,
                interview: 0,
                offer: 0,
                rejected: 0,
              }) as ApplicationCountsOut,
          ),
        ]);
        if (cancelled) return;
        setProfile(p);
        setRecent(v.slice(0, 5));
        setApplications(apps);
        setCounts(cnt);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  function recountFrom(list: ApplicationOut[]): ApplicationCountsOut {
    const out: ApplicationCountsOut = {
      saved: 0,
      applied: 0,
      interview: 0,
      offer: 0,
      rejected: 0,
    };
    for (const row of list) {
      out[row.status as keyof ApplicationCountsOut] += 1;
    }
    return out;
  }

  function applyChange(next: ApplicationOut): void {
    setApplications((prev) => {
      const updated = prev.map((row) => (row.id === next.id ? next : row));
      setCounts(recountFrom(updated));
      return updated;
    });
  }

  function applyRemove(id: number): void {
    setApplications((prev) => {
      const updated = prev.filter((row) => row.id !== id);
      setCounts(recountFrom(updated));
      return updated;
    });
  }

  if (!token) {
    return (
      <div className="relative min-h-[60vh] flex items-center justify-center">
        <HeroBackdrop />
        <div className="relative z-10 mx-auto flex max-w-md flex-col items-center gap-4 rounded-lg border border-border/80 bg-surface/80 backdrop-blur-md p-8 text-center shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded border border-border bg-elevated/40 text-text-tertiary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h2 className="text-[18px] font-[600] tracking-[-0.01em] text-white">Требуется авторизация</h2>
          <p className="text-[13px] leading-[1.6] text-text-secondary">
            {t("needsAuth")}
          </p>
          <Link href="/auth">
            <Button className="px-6 py-2 bg-accent hover:bg-accent-hover text-white rounded font-medium shadow-[0_4px_16px_rgba(99,102,241,0.2)]">
              {t("ctaLogin")}
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const stats = [
    { label: t("statSavedLabel"), value: counts?.saved ?? 0, icon: Bookmark },
    {
      label: t("statAppliedLabel"),
      value:
        (counts?.applied ?? 0) +
        (counts?.interview ?? 0) +
        (counts?.offer ?? 0) +
        (counts?.rejected ?? 0),
      icon: ClipboardList
    },
    { label: t("statViewsLabel"), value: 0, icon: LayoutGrid },
  ];

  const savedApplications = applications.filter((row) => row.status === "saved");

  return (
    <AppShell
      activeTab={tab}
      role="seeker"
      profileName={profile?.full_name || ""}
      profileSubtitle={profile?.target_role || "Соискатель"}
    >
      <FadeIn y={6} duration={0.3} immediate>
        <header className="mb-6 flex flex-col gap-1.5 border-b border-border/60 pb-5">
          <h1 className="text-[26px] font-[600] leading-tight tracking-[-0.02em] text-white">
            {t("title")}
          </h1>
          <p className="text-[13px] leading-[1.6] text-text-secondary">{t("subtitle")}</p>
        </header>
      </FadeIn>

      {tab === "overview" ? (
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

          <div className="flex flex-col gap-3">
            <div className="text-[11px] font-[600] uppercase tracking-[0.12em] text-text-tertiary">
              {t("recentTitle")}
            </div>
            {loading ? (
              <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 text-[13px] text-text-tertiary text-center">
                <span className="inline-block animate-pulse">Загрузка вакансий...</span>
              </div>
            ) : recent.length === 0 ? (
              <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-8 text-center text-[13px] text-text-tertiary">
                {t("recentEmpty")}
              </div>
            ) : (
              <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm px-4 shadow-[0_4px_24px_rgba(0,0,0,0.15)]">
                {recent.map((item) => (
                  <VacancyCard key={item.id} vacancy={item} />
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {tab === "saved" ? (
        <SavedList
          items={savedApplications}
          onAdvance={applyChange}
          onRemove={applyRemove}
        />
      ) : null}

      {tab === "applications" ? (
        <KanbanBoard
          items={applications}
          onChange={applyChange}
          onRemove={applyRemove}
        />
      ) : null}
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-text-tertiary text-sm">Загрузка...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
