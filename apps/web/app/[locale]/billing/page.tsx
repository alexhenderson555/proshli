// Pricing / billing page. Server component — renders three plan cards
// (Free, Pro, Team) and a small FAQ. There is no live payment hook-up
// yet; the CTAs route to /auth (free) or surface contact info (team).
// Pro will swap its CTA over to a checkout flow once ЮKassa is wired in.

import { getTranslations, setRequestLocale } from "next-intl/server";
import { FadeIn } from "@proshli/ui";
import { BillingPlans } from "@/components/billing-plans";

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
      <BillingPlans 
        plans={plans}
        featuresHeader={t("featuresHeader")}
        planProBadge={t("planProBadge")}
      />

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
