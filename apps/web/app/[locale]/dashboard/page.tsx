"use client";

// Seeker dashboard. Left rail nav (Overview / Saved / Applications /
// Settings) + main panel that flips view per tab. There are no
// `/seeker/saved` or `/seeker/applications` endpoints yet — those tabs
// render empty states with a hint, so the surface is real even while
// the backend catches up.

import { useEffect, useState } from "react";
import { LayoutGrid, Bookmark, ClipboardList, Settings as SettingsIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { Button } from "@/components/ui";
import { VacancyCard } from "@/components/vacancy-card";
import { FadeIn, Stagger } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { SeekerProfileOut, Vacancy } from "@/lib/types";
import { cn } from "@/lib/cn";

type Tab = "overview" | "saved" | "applications" | "settings";

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const [tab, setTab] = useState<Tab>("overview");
  const [token, setTokenValue] = useState<string | null>(null);
  const [profile, setProfile] = useState<SeekerProfileOut | null>(null);
  const [recent, setRecent] = useState<Vacancy[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTokenValue(getToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [p, v] = await Promise.all([
          // The seeker profile is optional — a brand-new account doesn't
          // have one yet, so we swallow 404s and keep the panel empty.
          api.seekerProfile(token!).catch(() => null),
          api.vacancies({}).catch(() => [] as Vacancy[]),
        ]);
        if (cancelled) return;
        setProfile(p);
        setRecent(v.slice(0, 5));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!token) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 rounded border border-border bg-surface p-8 text-center">
        <p className="text-[14px] text-text-secondary">{t("needsAuth")}</p>
        <Link href="/auth">
          <Button size="sm">{t("ctaLogin")}</Button>
        </Link>
      </div>
    );
  }

  const navItems: Array<{ key: Tab; label: string; Icon: typeof LayoutGrid }> = [
    { key: "overview", label: t("navOverview"), Icon: LayoutGrid },
    { key: "saved", label: t("navSaved"), Icon: Bookmark },
    { key: "applications", label: t("navApplications"), Icon: ClipboardList },
    { key: "settings", label: t("navSettings"), Icon: SettingsIcon },
  ];

  const stats = [
    { label: t("statSavedLabel"), value: 0 },
    { label: t("statAppliedLabel"), value: 0 },
    { label: t("statViewsLabel"), value: 0 },
  ];

  return (
    <div className="grid gap-6 py-6 lg:grid-cols-[220px_1fr]">
      {/* Left rail */}
      <aside className="flex flex-col gap-3 lg:sticky lg:top-20 lg:self-start">
        <nav className="flex flex-col gap-0.5 rounded border border-border bg-surface p-2">
          {navItems.map(({ key, label, Icon }) => {
            const active = tab === key;
            const className = cn(
              "flex items-center gap-2 rounded-sm px-2.5 py-1.5 text-[13px] font-[510] transition-colors",
              active
                ? "bg-elevated text-text-primary"
                : "text-text-tertiary hover:text-text-secondary",
            );
            if (key === "settings") {
              return (
                <Link key={key} href="/settings" className={className}>
                  <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                  {label}
                </Link>
              );
            }
            return (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={className + " text-left"}
              >
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                {label}
              </button>
            );
          })}
        </nav>

        {profile ? (
          <div className="flex items-center gap-2 rounded border border-border bg-surface p-2">
            <div
              className="flex h-7 w-7 items-center justify-center rounded bg-elevated text-[11px] font-[580] text-text-primary"
              aria-hidden="true"
            >
              {(profile.full_name || "?").slice(0, 1).toUpperCase()}
            </div>
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-[12px] font-[510] text-text-primary">
                {profile.full_name || "—"}
              </span>
              <span className="truncate text-[11px] text-text-tertiary">
                {profile.target_role || ""}
              </span>
            </div>
          </div>
        ) : null}
      </aside>

      {/* Main panel */}
      <section className="min-w-0">
        <FadeIn y={6} duration={0.3} immediate>
          <header className="mb-5 flex flex-col gap-1">
            <h1 className="text-[24px] font-[580] leading-tight tracking-[-0.02em] text-text-primary">
              {t("title")}
            </h1>
            <p className="text-[13px] leading-[1.55] text-text-secondary">{t("subtitle")}</p>
          </header>
        </FadeIn>

        {tab === "overview" ? (
          <div className="flex flex-col gap-5">
            <Stagger step={0.05} immediate className="grid gap-2 sm:grid-cols-3">
              {stats.map((stat) => (
                <div
                  key={stat.label}
                  className="flex flex-col gap-1 rounded border border-border bg-surface p-4"
                >
                  <div className="kicker">{stat.label}</div>
                  <div className="text-[22px] font-[580] tabular-nums tracking-[-0.02em] text-text-primary">
                    {stat.value}
                  </div>
                </div>
              ))}
            </Stagger>

            <div className="flex flex-col gap-2">
              <div className="kicker">{t("recentTitle")}</div>
              {loading ? (
                <div className="rounded border border-border bg-surface p-4 text-[13px] text-text-tertiary">
                  …
                </div>
              ) : recent.length === 0 ? (
                <div className="rounded border border-border bg-surface p-4 text-[13px] text-text-tertiary">
                  {t("recentEmpty")}
                </div>
              ) : (
                <div className="rounded border border-border bg-surface px-4">
                  {recent.map((item) => (
                    <VacancyCard key={item.id} vacancy={item} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}

        {tab === "saved" ? (
          <div className="flex flex-col gap-2">
            <div className="kicker">{t("savedTitle")}</div>
            <div className="rounded border border-border bg-surface p-6 text-center text-[13px] text-text-tertiary">
              {t("savedEmpty")}
            </div>
          </div>
        ) : null}

        {tab === "applications" ? (
          <div className="flex flex-col gap-2">
            <div className="kicker">{t("applicationsTitle")}</div>
            <div className="rounded border border-border bg-surface p-6 text-center text-[13px] text-text-tertiary">
              {t("applicationsEmpty")}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
