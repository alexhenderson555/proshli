"use client";

// Language switcher (RU / EN).
//
// Uses next-intl's locale-aware navigation so swapping locale preserves
// the current pathname. The middleware persists the new locale into the
// `PROSHLI_LOCALE` cookie (config in `i18n/routing.ts`) so server-rendered
// requests on subsequent navigation keep the choice.

import { useTransition } from "react";
import { Globe } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { usePathname } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

const FLAGS: Record<string, string> = {
  ru: "RU",
  en: "EN",
};

// `as-needed` mapping: RU has no prefix, EN gets `/en/...`.
function localePath(pathname: string, locale: string): string {
  // `pathname` from next-intl's `usePathname()` is the locale-stripped
  // path (e.g. `/vacancies`). Re-attach the prefix for non-default
  // locales; default locale keeps the bare path.
  if (locale === routing.defaultLocale) return pathname === "" ? "/" : pathname;
  return pathname === "/" ? `/${locale}` : `/${locale}${pathname}`;
}

export function LocaleSwitcher() {
  const t = useTranslations("header");
  const locale = useLocale();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  function onChange(next: string) {
    // Defence-in-depth: the `<select>` only emits values we render in
    // `<option>`, but a future code change or test that programmatically
    // sets `.value` could bypass the contract. Validate membership in
    // `routing.locales` before passing through.
    if (!(routing.locales as readonly string[]).includes(next)) return;
    if (next === locale) return;
    startTransition(() => {
      // Use a hard navigation rather than next-intl's soft `router.replace`.
      // The latter triggers a client-side route change but reuses the
      // cached root layout, leaving `<html lang>` and any server-rendered
      // strings pinned to the *previous* locale. A full document
      // navigation makes the proxy re-run, the cookie get set, and the
      // RSC tree re-render from scratch with the new locale.
      window.location.assign(localePath(pathname, next));
    });
  }

  return (
    <label className="relative inline-flex h-7 items-center rounded border border-border bg-elevated pl-2 pr-1 text-[11px] font-[510] text-text-secondary hover:border-border-strong transition-colors">
      <Globe className="h-3.5 w-3.5" aria-hidden="true" />
      <span className="sr-only">{t("languageAriaLabel")}</span>
      <select
        aria-label={t("languageAriaLabel")}
        value={locale}
        disabled={isPending}
        onChange={(event) => onChange(event.target.value)}
        className="ml-1 cursor-pointer appearance-none bg-transparent pr-3 text-[11px] font-[510] uppercase tracking-[0.08em] text-text-primary focus:outline-none"
      >
        {routing.locales.map((value) => (
          <option key={value} value={value}>
            {FLAGS[value] ?? value.toUpperCase()}
          </option>
        ))}
      </select>
    </label>
  );
}
