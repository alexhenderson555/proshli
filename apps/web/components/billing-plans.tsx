"use client";

import { useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

import { Link } from "@/i18n/navigation";
import { Stagger } from "@proshli/ui";
import { GlowCard } from "./glow-card";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";

type PlanKey = "free" | "pro" | "team";

interface PlanItem {
  key: PlanKey;
  name: string;
  price: string;
  period: string;
  desc: string;
  cta: string;
  href: string;
  features: string[];
  highlight?: boolean;
}

interface BillingPlansProps {
  plans: PlanItem[];
  featuresHeader: string;
  planProBadge: string;
}

export function BillingPlans({ plans, featuresHeader, planProBadge }: BillingPlansProps) {
  const router = useRouter();
  const [loadingKey, setLoadingKey] = useState<string | null>(null);

  const handleCheckout = async (planKey: string) => {
    const token = getToken();
    if (!token) {
      router.push(`/auth?mode=register&plan=${planKey}`);
      return;
    }

    try {
      setLoadingKey(planKey);
      const res = await api.checkout(token, planKey, window.location.href);
      if (res.confirmation_url) {
        window.location.assign(res.confirmation_url);
      }
    } catch (err) {
      console.error("Checkout failed", err);
      // Fallback or show toast
    } finally {
      setLoadingKey(null);
    }
  };

  return (
    <Stagger step={0.07} immediate className="grid gap-4 sm:grid-cols-3">
      {plans.map((plan) => {
        const isMailto = plan.href.startsWith("mailto:");
        const isCheckout = plan.key !== "free" && !isMailto;
        const isLoading = loadingKey === plan.key;
        
        const ctaClass = plan.highlight
          ? "inline-flex w-full items-center justify-center rounded bg-accent px-3 py-2 text-[13px] font-[510] text-white transition-colors hover:bg-accent-hover active:bg-accent-active disabled:opacity-50"
          : "inline-flex w-full items-center justify-center rounded border border-border bg-elevated px-3 py-2 text-[13px] font-[510] text-text-primary transition-colors hover:border-border-strong disabled:opacity-50";

        return (
          <GlowCard key={plan.key} className={plan.highlight ? "!border-accent" : ""}>
            <article className="relative flex h-full flex-col gap-5 p-5">
              {plan.highlight ? (
                <span className="absolute -top-2 left-4 inline-flex items-center rounded-sm border border-accent bg-canvas px-1.5 py-px text-[10px] font-[510] uppercase tracking-[0.1em] text-accent">
                  {planProBadge}
                </span>
              ) : null}

              <div className="flex flex-col gap-2">
                <div className="kicker text-[11px] font-[510] uppercase tracking-[0.1em] text-text-tertiary">{plan.name}</div>
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

              <div className="flex flex-col gap-2 border-t border-border pt-4 flex-grow">
                <div className="kicker text-[11px] font-[510] uppercase tracking-[0.1em] text-text-tertiary">{featuresHeader}</div>
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
              ) : isCheckout ? (
                <button 
                  onClick={() => handleCheckout(plan.key)} 
                  className={ctaClass}
                  disabled={isLoading}
                >
                  {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  {plan.cta}
                </button>
              ) : (
                <Link href={plan.href} className={ctaClass}>
                  {plan.cta}
                </Link>
              )}
            </article>
          </GlowCard>
        );
      })}
    </Stagger>
  );
}
