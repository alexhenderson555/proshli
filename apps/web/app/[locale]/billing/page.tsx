// Pricing / billing page. Server component — renders three plan cards
// (Free, Pro, Team) and a small FAQ. There is no live payment hook-up
// yet; the CTAs route to /auth (free) or surface contact info (team).
// Pro will swap its CTA over to a checkout flow once ЮKassa is wired in.

import { Check } from "lucide-react";
import { getTranslations, setRequestLocale } from "next-intl/server";

import { Link } from "@/i18n/navigation";
import { FadeIn, Stagger } from "@proshli/ui";

type PlanKey = "free" | "pro" | "team";

export default async function BillingPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("billing");

  const plans: Array<{
    key: PlanKey;
    name: string;
    price: string;
    period: string;
    desc: string;
    cta: string;
    href: string;
    features: string[];
    highlight?: boolean;
  }> = [
    {
      key: "free",
      name: t("planFreeName"),
      price: t("planFreePrice"),
      period: t("planFreePeriod"),
      desc: t("planFreeDesc"),
      cta: t("planFreeCta"),
      href: "/auth?mode=register",
      features: [t("featFreeFeed"), t("featFreeAi"), t("featFreeBasic")],
    },
    {
      key: "pro",
      name: t("planProName"),
      price: t("planProPrice"),
      period: t("planProPeriod"),
      desc: t("planProDesc"),
      cta: t("planProCta"),
      href: "/auth?mode=register&plan=pro",
      features: [
        t("featProUnlimitedAi"),
        t("featProTelegram"),
        t("featProSaved"),
        t("featProPriority"),
      ],
      highlight: true,
    },
    {
      key: "team",
      name: t("planTeamName"),
      price: t("planTeamPrice"),
      period: t("planTeamPeriod"),
      desc: t("planTeamDesc"),
      cta: t("planTeamCta"),
      href: "mailto:hello@proshli.ru",
      features: [
        t("featTeamSeats"),
        t("featTeamApi"),
        t("featTeamSla"),
        t("featTeamReports"),
      ],
    },
  ];

  const faqs: Array<{ q: string; a: string }> = [
    { q: t("faqQ1"), a: t("faqA1") },
    { q: t("faqQ2"), a: t("faqA2") },
    { q: t("faqQ3"), a: t("faqA3") },
    { q: t("faqQ4"), a: t("faqA4") },
  ];

  return (
    <div className="flex flex-col gap-14 py-10">
      {/* Header */}
      <FadeIn y={12} duration={0.45} immediate>
        <header className="mx-auto flex max-w-2xl flex-col items-center gap-3 text-center">
          <span className="inline-flex items-center gap-1.5 rounded border border-border bg-elevated px-2 py-1 text-[11px] font-[510] uppercase tracking-[0.1em] text-text-secondary">
            {t("badge")}
          </span>
          <h1 className="text-[36px] font-[580] leading-[1.05] tracking-[-0.03em] text-text-primary sm:text-[44px]">
            {t("title")}
          </h1>
          <p className="text-[15px] leading-[1.6] text-text-secondary">{t("subtitle")}</p>
        </header>
      </FadeIn>

      {/* Plans */}
      <Stagger step={0.07} immediate className="grid gap-4 sm:grid-cols-3">
        {plans.map((plan) => {
          const isMailto = plan.href.startsWith("mailto:");
          const ctaClass = plan.highlight
            ? "inline-flex w-full items-center justify-center rounded bg-accent px-3 py-2 text-[13px] font-[510] text-white transition-colors hover:bg-accent-hover active:bg-accent-active"
            : "inline-flex w-full items-center justify-center rounded border border-border bg-elevated px-3 py-2 text-[13px] font-[510] text-text-primary transition-colors hover:border-border-strong";
          return (
            <article
              key={plan.key}
              className={
                "relative flex flex-col gap-5 rounded border bg-surface p-5 " +
                (plan.highlight ? "border-accent" : "border-border")
              }
            >
              {plan.highlight ? (
                <span className="absolute -top-2 left-4 inline-flex items-center rounded-sm border border-accent bg-canvas px-1.5 py-px text-[10px] font-[510] uppercase tracking-[0.1em] text-accent">
                  {t("planProBadge")}
                </span>
              ) : null}

              <div className="flex flex-col gap-2">
                <div className="kicker">{plan.name}</div>
                <div className="flex items-baseline gap-2">
                  <span className="text-[32px] font-[580] tabular-nums leading-none tracking-[-0.02em] text-text-primary">
                    {plan.price}
                  </span>
                  <span className="text-[12px] font-[510] text-text-tertiary">
                    {plan.period}
                  </span>
                </div>
                <p className="text-[13px] leading-[1.55] text-text-secondary">{plan.desc}</p>
              </div>

              <div className="flex flex-col gap-2 border-t border-border pt-4">
                <div className="kicker">{t("featuresHeader")}</div>
                <ul className="flex flex-col gap-1.5">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-[13px] leading-[1.5] text-text-secondary"
                    >
                      <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent" aria-hidden="true" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {isMailto ? (
                <a href={plan.href} className={ctaClass}>
                  {plan.cta}
                </a>
              ) : (
                <Link href={plan.href} className={ctaClass}>
                  {plan.cta}
                </Link>
              )}
            </article>
          );
        })}
      </Stagger>

      {/* FAQ — bordered list, no fancy accordion */}
      <section className="mx-auto flex w-full max-w-2xl flex-col gap-3">
        <div className="kicker">{t("faqTitle")}</div>
        <dl className="flex flex-col">
          {faqs.map((faq) => (
            <details
              key={faq.q}
              className="group border-b border-border py-3 last:border-b-0"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-[14px] font-[510] text-text-primary marker:hidden">
                <span>{faq.q}</span>
                <span
                  className="text-[18px] leading-none text-text-tertiary transition-transform group-open:rotate-45"
                  aria-hidden="true"
                >
                  +
                </span>
              </summary>
              <p className="mt-2 text-[13px] leading-[1.6] text-text-secondary">{faq.a}</p>
            </details>
          ))}
        </dl>
      </section>
    </div>
  );
}
