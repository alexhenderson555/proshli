"use client";

// Language switcher (RU / EN).
//
// Uses next-intl's locale-aware navigation so swapping locale preserves
// the current pathname. The middleware persists the new locale into the
// `OTKLIK_LOCALE` cookie (config in `i18n/routing.ts`) so server-rendered
// requests on subsequent navigation keep the choice.

import { useTransition } from "react";
import { Globe } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { usePathname, useRouter } from "@/i18n/navigation";
import { routing } from "@/i18n/routing";

const FLAGS: Record<string, string> = {
  ru: "RU",
  en: "EN",
};

export function LocaleSwitcher() {
  const t = useTranslations("header");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  function onChange(next: string) {
    // Defence-in-depth: the `<select>` only emits values we render in
    // `<option>`, but a future code change or test that programmatically
    // sets `.value` could bypass the contract. Validate membership in
    // `routing.locales` before passing to the typed router API.
    if (!(routing.locales as readonly string[]).includes(next)) return;
    startTransition(() => {
      // `next-intl`'s router accepts the typed locale param to switch
      // languages while preserving the current pathname.
      router.replace(pathname, { locale: next as (typeof routing.locales)[number] });
    });
  }

  return (
    <label className="relative inline-flex h-9 items-center rounded-lg border border-border bg-card pl-2 pr-1 text-xs font-semibold text-muted-foreground">
      <Globe className="h-4 w-4" aria-hidden="true" />
      <span className="sr-only">{t("languageAriaLabel")}</span>
      <select
        aria-label={t("languageAriaLabel")}
        value={locale}
        disabled={isPending}
        onChange={(event) => onChange(event.target.value)}
        className="ml-1 cursor-pointer appearance-none bg-transparent pr-4 text-xs font-semibold uppercase tracking-wider text-foreground focus:outline-none"
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
