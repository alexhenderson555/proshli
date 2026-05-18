// Landing page. Server component — translations resolved at request time
// via `getTranslations`. Three sections: hero (intro + AI demo panel),
// features (4-tile grid), bottom CTA. All motion is mount-only via the
// shared FadeIn / Stagger primitives so the page never re-animates on
// route re-entry.

import { ArrowRight, Bot, Filter, Sparkles, Zap } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AiChatPanel } from "@/features/ai-chat/ai-chat-panel";
import { Link } from "@/i18n/navigation";
import { Stagger } from "@proshli/ui";

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  // Re-pin the locale here even though the layout did it — static
  // rendering needs every page to call setRequestLocale so the locale
  // is baked into the RSC payload.
  setRequestLocale(locale);
  const t = await getTranslations("landing");

  const features = [
    { icon: Sparkles, title: t("feature1Title"), body: t("feature1Body") },
    { icon: Filter, title: t("feature2Title"), body: t("feature2Body") },
    { icon: Bot, title: t("feature3Title"), body: t("feature3Body") },
    { icon: Zap, title: t("feature4Title"), body: t("feature4Body") },
  ] as const;

  const metrics = [
    { value: t("metricSourcesValue"), label: t("metricSourcesLabel") },
    { value: t("metricSpeedValue"), label: t("metricSpeedLabel") },
    { value: t("metricAvailabilityValue"), label: t("metricAvailabilityLabel") },
  ] as const;

  return (
    <div className="flex flex-col gap-20 py-10">
      {/* Hero — left column copy + CTAs + metric strip, right column AI demo.
          The hero deliberately renders without a `<FadeIn>` motion wrapper:
          Playwright's `strict mode` selectors observed framer-motion's
          presence/initial pair as two separate DOM nodes for the heading
          span, which broke `getByText` even when only one node was visible.
          The features grid below still uses `<Stagger>`, so the landing
          still feels animated on first paint. */}
      <section className="grid gap-10 lg:grid-cols-[1.15fr_1fr] lg:items-center">
        <div>
          <div className="flex flex-col gap-6">
            <span className="inline-flex w-fit items-center gap-1.5 rounded border border-border bg-elevated px-2 py-1 text-[11px] font-[510] uppercase tracking-[0.1em] text-text-secondary">
              <Sparkles className="h-3 w-3 text-accent" aria-hidden="true" />
              {t("badge")}
            </span>
            <h1 className="text-balance text-[40px] font-[580] leading-[1.05] tracking-[-0.03em] text-text-primary sm:text-[48px] lg:text-[56px]">
              {t("heroTitleLead")}{" "}
              <span className="text-accent">{t("heroTitleAccent")}</span>.
            </h1>
            <p className="max-w-xl text-pretty text-[15px] leading-[1.6] text-text-secondary">
              {t("heroSubtitle")}
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <Link
                href="/auth?mode=register"
                className="inline-flex items-center gap-1.5 rounded bg-accent px-4 py-2 text-[13px] font-[510] text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
              >
                {t("ctaPrimary")}
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
              <Link
                href="/vacancies"
                className="inline-flex items-center gap-1.5 rounded border border-border bg-elevated px-4 py-2 text-[13px] font-[510] text-text-primary transition-colors hover:border-border-strong"
              >
                {t("ctaSecondary")}
              </Link>
            </div>
            <dl className="mt-3 grid max-w-md grid-cols-3 gap-6">
              {metrics.map((m) => (
                <div key={m.label} className="flex flex-col gap-1">
                  <dt className="text-[22px] font-[580] tabular-nums tracking-[-0.02em] text-text-primary">
                    {m.value}
                  </dt>
                  <dd className="text-[10px] font-[510] uppercase tracking-[0.1em] text-text-tertiary">
                    {m.label}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>

        <AiChatPanel />
      </section>

      {/* Features — flat editorial grid, no lift, hover = border tint only */}
      <section className="flex flex-col gap-6">
        <div className="flex flex-col gap-1.5">
          <div className="kicker">{t("featuresKicker") || "Features"}</div>
          <h2 className="text-[28px] font-[580] leading-tight tracking-[-0.02em] text-text-primary sm:text-[32px]">
            {t("featuresTitle")}
          </h2>
          <p className="max-w-2xl text-[14px] leading-[1.6] text-text-secondary">
            {t("featuresSubtitle")}
          </p>
        </div>
        <Stagger step={0.06} immediate className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, body }) => (
            <article
              key={title}
              className="flex flex-col gap-3 rounded border border-border bg-surface p-4 transition-colors hover:border-border-strong"
            >
              <div className="inline-flex h-8 w-8 items-center justify-center rounded bg-elevated text-accent">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <h3 className="text-[14px] font-[580] tracking-[-0.01em] text-text-primary">
                {title}
              </h3>
              <p className="text-[13px] leading-[1.55] text-text-secondary">{body}</p>
            </article>
          ))}
        </Stagger>
      </section>

      {/* Bottom CTA — flat panel, no gradient */}
      <section className="flex flex-col items-start gap-4 rounded border border-border bg-surface p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
        <div className="flex flex-col gap-1.5">
          <h2 className="text-[22px] font-[580] leading-tight tracking-[-0.02em] text-text-primary sm:text-[26px]">
            {t("ctaSectionTitle")}
          </h2>
          <p className="max-w-xl text-[13px] leading-[1.55] text-text-secondary">
            {t("ctaSectionSubtitle")}
          </p>
        </div>
        <Link
          href="/auth?mode=register"
          className="inline-flex shrink-0 items-center gap-1.5 rounded bg-accent px-4 py-2 text-[13px] font-[510] text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
        >
          {t("ctaSectionButton")}
          <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
        </Link>
      </section>
    </div>
  );
}
