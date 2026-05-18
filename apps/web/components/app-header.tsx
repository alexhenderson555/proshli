"use client";

// Top navigation. Editorial dense: 52px row, hairline bottom, flat brand
// mark, segmented active state on the centre nav. Sticky so the canvas
// can scroll under it with backdrop-blur for legibility.
//
// Auth-awareness reads the JWT from localStorage and flips the right-side
// CTA — same behaviour as before, just visually quieter. The dashboard
// link only appears when authed.

import { useSyncExternalStore } from "react";
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
      window.localStorage.getItem("proshli_web_token") ??
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
    { href: "/billing", label: t("navBilling") },
    { href: "/seeker", label: t("navSeeker") },
    { href: "/employer", label: t("navEmployer") },
  ] as const;

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-canvas/85 backdrop-blur-md">
      <div className="container flex items-center justify-between gap-6 py-2.5">
        <Link
          href="/"
          className="flex items-center gap-2 focus-ring"
          aria-label={t("brandAriaLabel")}
        >
          <span
            className="inline-flex h-6 w-6 items-center justify-center rounded-sm bg-accent text-white font-[580] text-[12px] leading-none"
            aria-hidden="true"
          >
            P
          </span>
          <span className="text-[13px] font-[580] tracking-[-0.02em] text-text-primary">
            Proshli
          </span>
        </Link>

        <nav
          className="hidden md:flex items-center gap-0.5"
          aria-label={t("navAriaLabel")}
        >
          {nav.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={
                  active
                    ? "rounded px-2.5 py-1.5 text-[13px] font-[510] text-text-primary bg-elevated transition-colors"
                    : "rounded px-2.5 py-1.5 text-[13px] font-[510] text-text-tertiary hover:text-text-primary hover:bg-elevated transition-colors"
                }
                aria-current={active ? "page" : undefined}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-1.5">
          <LocaleSwitcher />
          <ThemeSwitcher />
          {authed ? (
            <Link
              href="/dashboard"
              className="rounded bg-accent px-2.5 py-1.5 text-[13px] font-[510] text-white transition-colors hover:bg-accent-hover"
            >
              {t("ctaDashboard")}
            </Link>
          ) : (
            <>
              <Link
                href="/auth?mode=login"
                className="hidden sm:inline-block rounded px-2 py-1.5 text-[13px] font-[510] text-text-secondary hover:text-text-primary hover:bg-elevated transition-colors"
              >
                {t("ctaLogin")}
              </Link>
              <Link
                href="/auth?mode=register"
                className="rounded bg-accent px-2.5 py-1.5 text-[13px] font-[510] text-white transition-colors hover:bg-accent-hover"
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
