import { ArrowRight, Bot, Filter, Sparkles, Zap } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { AiChatPanel } from "@/features/ai-chat/ai-chat-panel";
import { Link } from "@/i18n/navigation";

// Server component — translations resolved at request time.
//
// Why `setRequestLocale` again here even though the parent layout does
// it: per next-intl docs, every static-render-eligible page must call
// it so the locale gets baked into the page's RSC payload, otherwise
// `generateStaticParams` works but `getTranslations` won't have the
// right locale during the static export.

export default async function Home({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
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
    <div className="flex flex-col gap-16 py-8">
      {/* Hero */}
      <section className="grid gap-10 lg:grid-cols-[1.2fr_1fr] lg:items-center">
        <div className="flex flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            {t("badge")}
          </span>
          <h1 className="text-balance text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            {t("heroTitleLead")}{" "}
            <span className="bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--accent))] bg-clip-text text-transparent">
              {t("heroTitleAccent")}
            </span>
            .
          </h1>
          <p className="max-w-2xl text-pretty text-base text-muted-foreground sm:text-lg">
            {t("heroSubtitle")}
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/auth?mode=register"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
            >
              {t("ctaPrimary")}
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/vacancies"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:bg-muted"
            >
              {t("ctaSecondary")}
            </Link>
          </div>
          <dl className="mt-4 grid max-w-md grid-cols-3 gap-6">
            {metrics.map((m) => (
              <div key={m.label} className="flex flex-col gap-1">
                <dt className="text-2xl font-extrabold tracking-tight text-foreground">{m.value}</dt>
                <dd className="text-xs text-muted-foreground">{m.label}</dd>
              </div>
            ))}
          </dl>
        </div>

        <AiChatPanel />
      </section>

      {/* Features */}
      <section className="flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            {t("featuresTitle")}
          </h2>
          <p className="max-w-2xl text-muted-foreground">{t("featuresSubtitle")}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, body }) => (
            <article
              key={title}
              className="panel flex flex-col gap-3 p-5 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold">{title}</h3>
              <p className="text-sm text-muted-foreground">{body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="panel flex flex-col items-start gap-4 p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10">
        <div className="flex flex-col gap-2">
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
            {t("ctaSectionTitle")}
          </h2>
          <p className="max-w-xl text-muted-foreground">{t("ctaSectionSubtitle")}</p>
        </div>
        <Link
          href="/auth?mode=register"
          className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
        >
          {t("ctaSectionButton")}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
