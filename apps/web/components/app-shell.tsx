"use client";

import { useTranslations } from "next-intl";
import { LayoutGrid, Bookmark, ClipboardList, Settings as SettingsIcon, Briefcase, BarChart3, Users, FileText } from "lucide-react";

import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/cn";
import { HeroBackdrop } from "./hero-backdrop";

export type Role = "seeker" | "employer";
export type TabKey = "overview" | "saved" | "applications" | "settings" | "vacancies" | "analytics" | "candidates" | "resume";

interface AppShellProps {
  children: React.ReactNode;
  activeTab: TabKey;
  role?: Role;
  profileName?: string;
  profileSubtitle?: string;
}

export function AppShell({ children, activeTab, role = "seeker", profileName, profileSubtitle }: AppShellProps) {
  const t = useTranslations("dashboard");

  const seekerNav = [
    { key: "overview", label: t("navOverview"), Icon: LayoutGrid, href: "/dashboard" },
    { key: "saved", label: t("navSaved"), Icon: Bookmark, href: "/dashboard?tab=saved" },
    { key: "applications", label: t("navApplications"), Icon: ClipboardList, href: "/dashboard?tab=applications" },
    { key: "resume", label: "Мои резюме", Icon: FileText, href: "/resume" },
    { key: "settings", label: t("navSettings"), Icon: SettingsIcon, href: "/settings" },
  ];

  const employerNav = [
    { key: "overview", label: "Обзор", Icon: LayoutGrid, href: "/employer" },
    { key: "vacancies", label: "Вакансии", Icon: Briefcase, href: "/employer?tab=vacancies" },
    { key: "candidates", label: "Отклики", Icon: Users, href: "/employer?tab=candidates" },
    { key: "analytics", label: "Аналитика", Icon: BarChart3, href: "/employer?tab=analytics" },
    { key: "settings", label: t("navSettings"), Icon: SettingsIcon, href: "/settings" },
  ];

  const navItems = role === "employer" ? employerNav : seekerNav;

  return (
    <div className="relative min-h-screen">
      <HeroBackdrop />

      <div className="grid gap-8 py-8 lg:grid-cols-[240px_1fr] relative z-10">
        {/* Left rail */}
        <aside className="flex flex-col gap-4 lg:sticky lg:top-24 lg:self-start">
          <nav className="flex flex-col gap-1 rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-2 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
            {navItems.map(({ key, label, Icon, href }) => {
              const active = activeTab === key;
              const className = cn(
                "flex items-center gap-2.5 rounded px-3 py-2 text-[13px] font-[550] transition-all duration-150",
                active
                  ? "bg-white/[0.04] text-white border-l-2 border-accent pl-2.5"
                  : "text-text-secondary hover:text-white hover:bg-white/[0.02]",
              );
              return (
                <Link key={key} href={href} className={className}>
                  <Icon className={cn("h-4 w-4 shrink-0 transition-colors", active ? "text-accent" : "text-text-tertiary")} aria-hidden="true" />
                  {label}
                </Link>
              );
            })}
          </nav>

          {profileName ? (
            <div className="flex items-center gap-3 rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-3 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
              <div
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded bg-accent/15 border border-accent/20 text-[12px] font-[600] text-accent"
                aria-hidden="true"
              >
                {(profileName || "?").slice(0, 1).toUpperCase()}
              </div>
              <div className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-[12px] font-[600] text-white">
                  {profileName || "—"}
                </span>
                <span className="truncate text-[11px] text-text-tertiary">
                  {profileSubtitle || (role === "employer" ? "Работодатель" : "Соискатель")}
                </span>
              </div>
            </div>
          ) : null}
        </aside>

        {/* Main panel */}
        <section className="min-w-0">
          {children}
        </section>
      </div>
    </div>
  );
}
