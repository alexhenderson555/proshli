"use client";

// Top navigation bar. Brand mark on the left, navigation in the middle,
// auth CTA on the right. Stays sticky as you scroll.
//
// Auth-awareness is intentionally light right now: we read a
// `otklik.session` cookie/localStorage entry written by the legacy
// pages and flip the right-side CTA accordingly. The proper cookie
// middleware lands in Wave 7b once the API is on /v1.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSyncExternalStore } from "react";
import { Sparkles } from "lucide-react";

const nav = [
  { href: "/vacancies", label: "Вакансии" },
  { href: "/seeker", label: "Соискатель" },
  { href: "/employer", label: "Работодатель" },
];

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
    return window.localStorage.getItem("otklik.token");
  } catch {
    return null;
  }
}

function getServerTokenSnapshot() {
  return null;
}

export function AppHeader() {
  const pathname = usePathname();
  const token = useSyncExternalStore(subscribeToToken, getTokenSnapshot, getServerTokenSnapshot);
  const authed = Boolean(token);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur">
      <div className="container flex items-center justify-between gap-4 py-3">
        <Link href="/" className="flex items-center gap-2.5" aria-label="Otklik.ai — на главную">
          <span
            className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--accent))] text-primary-foreground shadow-sm"
            aria-hidden="true"
          >
            <Sparkles className="h-4 w-4" />
          </span>
          <div className="leading-tight">
            <div className="text-sm font-extrabold tracking-tight">Otklik.ai</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
              AI job aggregator
            </div>
          </div>
        </Link>
        <nav className="hidden flex-wrap items-center gap-1 md:flex" aria-label="Основная навигация">
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
          {authed ? (
            <Link
              href="/seeker"
              className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
            >
              Кабинет
            </Link>
          ) : (
            <>
              <Link
                href="/auth?mode=login"
                className="hidden rounded-lg px-3 py-2 text-sm font-semibold text-muted-foreground transition hover:bg-muted hover:text-foreground sm:inline-block"
              >
                Войти
              </Link>
              <Link
                href="/auth?mode=register"
                className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
              >
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
