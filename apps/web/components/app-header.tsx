"use client";

// Top navigation bar. Brand mark on the left, navigation in the middle,
// auth CTA on the right plus locale + theme switchers. Stays sticky as
// you scroll.
//
// Auth-awareness is intentionally light right now: we read the JWT token
// from localStorage and flip the right-side CTA accordingly. Server-side
// cookie auth lives in `lib/session.ts`.

import { useSyncExternalStore } from "react";
import { Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";

import { Link, usePathname } from "@/i18n/navigation";
import { LocaleSwitcher } from "./locale-switcher";
import { ThemeSwitcher } from "./theme-switcher";

// `useSyncExternalStore`-friendly view over localStorage. Avoids the
// classic `useEffect`-then-setState pattern (which trips React 19's
// `react-hooks/set-state-in-effect` rule) and gives us SSR safety
// via the `serverSnapshot` parameter for free.

function subscribeToToken(cb: () => void) {
  if (typeof window === "undefined") return () => {};
  window.addEventListener("storage", cb);
  return () => window.removeEventListener("storage", cb);
}

function getTokenSnapshot() {
  if (typeof window === "undefined") return null;
  try {
    // Keep in sync with `lib/session.ts` `TOKEN_KEY`.
    return (
      window.localStorage.getItem("otklik_web_token") ??
      window.localStorage.getItem("jobskout_web_token")
    );
  } catch {
    return null;
  }
}

function getServerTokenSnapshot() {
  return null;
}

export function AppHeader() {
  const t = useTranslations("header");
  const pathname = usePathname();
  const token = useSyncExternalStore(subscribeToToken, getTokenSnapshot, getServerTokenSnapshot);
  const authed = Boolean(token);

  const nav = [
    { href: "/vacancies", label: t("navVacancies") },
    { href: "/seeker", label: t("navSeeker") },
    { href: "/employer", label: t("navEmployer") },
  ] as const;

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur">
      <div className="container flex items-center justify-between gap-4 py-3">
        <Link href="/" className="flex items-center gap-2.5" aria-label={t("brandAriaLabel")}>
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--accent))] text-primary-foreground shadow-sm"
            aria-hidden="true"
          >
            <Sparkles className="h-4 w-4" />
          </span>
          <div className="leading-tight">
            <div className="text-sm font-extrabold tracking-tight">Otklik.ai</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {t("brandSubtitle")}
            </div>
          </div>
        </Link>
        <nav className="hidden flex-wrap items-center gap-1 md:flex" aria-label={t("navAriaLabel")}>
          {nav.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                }`}
                aria-current={active ? "page" : undefined}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="flex items-center gap-2">
          <LocaleSwitcher />
          <ThemeSwitcher />
          {authed ? (
            <Link
              href="/seeker"
              className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
            >
              {t("ctaDashboard")}
            </Link>
          ) : (
            <>
              <Link
                href="/auth?mode=login"
                className="hidden rounded-lg px-3 py-2 text-sm font-semibold text-muted-foreground transition hover:bg-muted hover:text-foreground sm:inline-block"
              >
                {t("ctaLogin")}
              </Link>
              <Link
                href="/auth?mode=register"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
              >
                {t("ctaRegister")}
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
