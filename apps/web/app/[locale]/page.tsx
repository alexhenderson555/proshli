// Landing page. Server component — translations resolved at request time
// via `getTranslations`. Sections: hero (intro + live counters + AI demo
// panel), features grid, HH-vs-Proshli comparison, founder note, bottom
// CTA. The hero counters come from a server-side fetch of
// `/vacancies/stats`; failure degrades silently to the i18n fallback
// placeholder ("—") so the page never flashes broken numbers.

import { ArrowRight, Bot, Filter, Sparkles, Zap, Keyboard } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AiChatPanel } from "@/features/ai-chat/ai-chat-panel";
import { Link } from "@/i18n/navigation";
import type { VacancyStatsOut } from "@/lib/types";
import { Stagger } from "@proshli/ui";
import { HeroBackdrop } from "@/components/hero-backdrop";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function fetchStats(): Promise<VacancyStatsOut | null> {
  try {
    const res = await fetch(`${API_BASE}/vacancies/stats`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as VacancyStatsOut;
  } catch {
    return null;
  }
}

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("landing");
  const stats = await fetchStats();

  const features = [
    { icon: Sparkles, title: t("feature1Title"), body: t("feature1Body") },
    { icon: Filter, title: t("feature2Title"), body: t("feature2Body") },
    { icon: Bot, title: t("feature3Title"), body: t("feature3Body") },
    { icon: Zap, title: t("feature4Title"), body: t("feature4Body") },
  ] as const;

  const fallback = t("metricFallback");
  const fmt = (n: number | undefined) =>
    typeof n === "number" ? new Intl.NumberFormat(locale).format(n) : fallback;

  const metrics = [
    { value: fmt(stats?.total), label: t("metricTotalLabel") },
    { value: fmt(stats?.last_24h), label: t("metric24hLabel") },
    { value: fmt(stats?.sources), label: t("metricSourcesLabel") },
  ] as const;

  const hhPoints = [t("vsHhHhPoint1"), t("vsHhHhPoint2"), t("vsHhHhPoint3")] as const;
  const proshliPoints = [
    t("vsHhProshliPoint1"),
    t("vsHhProshliPoint2"),
    t("vsHhProshliPoint3"),
  ] as const;

  return (
    <div className="relative min-h-screen">
      <HeroBackdrop />

      <div className="flex flex-col gap-24 py-16">
        {/* Hero — left column copy + CTAs + metric strip, right column AI demo. */}
        <section className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div className="flex flex-col justify-center">
            <div className="flex flex-col gap-6">
              {/* Premium Glow Badge */}
              <div className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3.5 py-1 text-[11px] font-[550] uppercase tracking-[0.12em] text-text-secondary shadow-[0_0_15px_rgba(255,255,255,0.02)]">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-accent"></span>
                </span>
                <span className="bg-gradient-to-r from-text-primary to-text-secondary bg-clip-text text-transparent">
                  {t("badge")}
                </span>
              </div>

              {/* Sharp Typography Heading */}
              <h1 className="text-balance text-[44px] font-[600] leading-[1.05] tracking-[-0.03em] text-white sm:text-[54px] lg:text-[62px]">
                {t("heroTitleLead")}{" "}
                <span className="bg-gradient-to-r from-accent to-indigo-400 bg-clip-text text-transparent">
                  {t("heroTitleAccent")}
                </span>.
              </h1>

              {/* Subtitle */}
              <p className="max-w-xl text-pretty text-[15px] leading-[1.6] text-text-secondary">
                {t("heroSubtitle")}
              </p>

              {/* CTAs & Shortcuts */}
              <div className="flex flex-wrap items-center gap-4">
                <Link
                  href="/auth?mode=register"
                  className="inline-flex items-center gap-2 rounded bg-accent px-5 py-2.5 text-[13px] font-[550] text-white shadow-[0_4px_20px_rgba(99,102,241,0.25)] transition-all duration-200 hover:bg-accent-hover hover:shadow-[0_4px_24px_rgba(99,102,241,0.35)] active:bg-accent-active"
                >
                  {t("ctaPrimary")}
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
                <Link
                  href="/vacancies"
                  className="inline-flex items-center gap-2 rounded border border-border bg-surface/40 backdrop-blur-sm px-5 py-2.5 text-[13px] font-[550] text-text-primary transition-all duration-200 hover:border-border-strong hover:bg-surface/60"
                >
                  {t("ctaSecondary")}
                </Link>
                
                {/* Keyboard Shortcut Indicator */}
                <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-[510] text-text-tertiary border border-border bg-surface/20 px-2.5 py-1.5 rounded ml-2">
                  <Keyboard className="h-3.5 w-3.5" />
                  <span>Нажми <kbd className="font-mono text-text-secondary bg-elevated px-1 py-0.5 rounded border border-border">⌘K</kbd> для меню</span>
                </div>
              </div>

              {/* Stats Grid */}
              <dl className="mt-6 grid max-w-md grid-cols-3 gap-8 border-t border-border/60 pt-6">
                {metrics.map((m) => (
                  <div key={m.label} className="flex flex-col gap-1">
                    <dt className="text-[24px] font-[600] tabular-nums tracking-[-0.02em] text-white bg-gradient-to-b from-white to-text-secondary bg-clip-text text-transparent">
                      {m.value}
                    </dt>
                    <dd className="text-[10px] font-[550] uppercase tracking-[0.12em] text-text-tertiary">
                      {m.label}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>

          {/* AI Panel Right Column with Subtle Container Glow */}
          <div className="relative">
            <div className="absolute -inset-1 rounded-xl bg-gradient-to-r from-accent/10 to-indigo-500/10 opacity-30 blur-lg" />
            <AiChatPanel className="relative z-10 border-border/80 bg-surface/75 backdrop-blur-md shadow-[0_8px_32px_rgba(0,0,0,0.4)]" />
          </div>
        </section>

        {/* Features — bento editorial grid */}
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-[600] uppercase tracking-[0.18em] text-accent">
              {t("featuresKicker") || "Features"}
            </div>
            <h2 className="text-[30px] font-[600] leading-tight tracking-[-0.03em] text-white sm:text-[36px]">
              {t("featuresTitle")}
            </h2>
            <p className="max-w-2xl text-[14px] leading-[1.6] text-text-secondary">
              {t("featuresSubtitle")}
            </p>
          </div>
          <Stagger step={0.06} immediate className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, body }) => (
              <article
                key={title}
                className="flex flex-col gap-4 rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-5 transition-all duration-300 hover:border-accent/40 hover:bg-surface/50 hover:shadow-[0_4px_20px_rgba(99,102,241,0.03)] group"
              >
                <div className="inline-flex h-9 w-9 items-center justify-center rounded border border-border bg-elevated/40 text-text-secondary group-hover:text-accent group-hover:border-accent/30 transition-colors">
                  <Icon className="h-4.5 w-4.5" aria-hidden="true" />
                </div>
                <div className="flex flex-col gap-1.5">
                  <h3 className="text-[14px] font-[600] tracking-[-0.01em] text-text-primary group-hover:text-white transition-colors">
                    {title}
                  </h3>
                  <p className="text-[13px] leading-[1.6] text-text-secondary">{body}</p>
                </div>
              </article>
            ))}
          </Stagger>
        </section>

        {/* HH vs Proshli — Two-column compared in Terminal Mockup style */}
        <section className="flex flex-col gap-8">
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-[600] uppercase tracking-[0.18em] text-accent">
              {t("vsHhKicker")}
            </div>
            <h2 className="text-[30px] font-[600] leading-tight tracking-[-0.03em] text-white sm:text-[36px]">
              {t("vsHhTitle")}
            </h2>
            <p className="max-w-2xl text-[14px] leading-[1.6] text-text-secondary">
              {t("vsHhSubtitle")}
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2">
            {/* HH Terminal */}
            <article className="flex flex-col gap-4 rounded-lg border border-border/80 bg-surface/20 p-6 relative overflow-hidden">
              <div className="absolute top-3 right-3 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-white/10" />
                <span className="h-2 w-2 rounded-full bg-white/10" />
                <span className="h-2 w-2 rounded-full bg-white/10" />
              </div>
              <h3 className="text-[12px] font-[600] uppercase tracking-[0.12em] text-text-tertiary">
                {t("vsHhHhHeading")}
              </h3>
              <ul className="flex flex-col gap-3 text-[13px] leading-[1.6] text-text-secondary mt-2">
                {hhPoints.map((point) => (
                  <li key={point} className="flex gap-3">
                    <span className="text-red-400 font-mono select-none shrink-0">✕</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>

            {/* Proshli Terminal */}
            <article className="flex flex-col gap-4 rounded-lg border border-accent/30 bg-accent/[0.01] p-6 relative overflow-hidden shadow-[0_8px_32px_rgba(99,102,241,0.03)]">
              <div className="absolute top-3 right-3 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-accent/30" />
                <span className="h-2 w-2 rounded-full bg-accent/30" />
                <span className="h-2 w-2 rounded-full bg-accent/30" />
              </div>
              <h3 className="text-[12px] font-[600] uppercase tracking-[0.12em] text-accent">
                {t("vsHhProshliHeading")}
              </h3>
              <ul className="flex flex-col gap-3 text-[13px] leading-[1.6] text-text-primary mt-2">
                {proshliPoints.map((point) => (
                  <li key={point} className="flex gap-3">
                    <span className="text-accent font-mono select-none shrink-0">✓</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </article>
          </div>
        </section>

        {/* Founder note — elegant quote card */}
        <section className="flex flex-col gap-4 rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-8 sm:p-10 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 rounded-full bg-accent/5 blur-2xl pointer-events-none" />
          <div className="text-[11px] font-[600] uppercase tracking-[0.18em] text-accent">
            {t("founderKicker")}
          </div>
          <h2 className="text-[24px] font-[600] leading-tight tracking-[-0.02em] text-white sm:text-[28px]">
            {t("founderTitle")}
          </h2>
          <p className="max-w-3xl text-[14px] leading-[1.65] text-text-secondary italic">
            &ldquo;{t("founderBody")}&rdquo;
          </p>
          <div className="flex items-center gap-3 mt-2">
            <div className="h-6 w-1 bg-accent rounded-full" />
            <p className="text-[12px] font-[600] uppercase tracking-[0.1em] text-text-primary">
              {t("founderSignoff")}
            </p>
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="flex flex-col items-start gap-6 rounded-lg border border-border/80 bg-surface/40 backdrop-blur-sm p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10 relative overflow-hidden">
          <div className="absolute -inset-x-20 -inset-y-40 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.03)_0%,transparent_70%)] pointer-events-none" />
          <div className="flex flex-col gap-1.5 relative z-10">
            <h2 className="text-[24px] font-[600] leading-tight tracking-[-0.02em] text-white sm:text-[28px]">
              {t("ctaSectionTitle")}
            </h2>
            <p className="max-w-xl text-[13px] leading-[1.6] text-text-secondary">
              {t("ctaSectionSubtitle")}
            </p>
          </div>
          <Link
            href="/auth?mode=register"
            className="inline-flex shrink-0 items-center gap-2 rounded bg-accent px-5 py-2.5 text-[13px] font-[550] text-white shadow-[0_4px_20px_rgba(99,102,241,0.2)] transition-all duration-200 hover:bg-accent-hover hover:shadow-[0_4px_24px_rgba(99,102,241,0.3)] active:bg-accent-active relative z-10"
          >
            {t("ctaSectionButton")}
            <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </section>
      </div>
    </div>
  );
}
