// Central next-intl routing configuration.
//
// We support Russian (default) and English. The `as-needed` locale prefix
// keeps RU URLs clean — `/vacancies` stays `/vacancies` — and prefixes
// English with `/en`. This is the strategy recommended by the next-intl
// docs for an i18n rollout on an existing single-locale app where the
// public RU URLs must not change for SEO reasons.
//
// Shared by:
//   - `proxy.ts` (locale negotiation & rewrite)
//   - `i18n/request.ts` (per-request message loading)
//   - `i18n/navigation.ts` (typed Link / useRouter helpers)

import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["ru", "en"] as const,
  defaultLocale: "ru",
  // `as-needed` — RU URLs have no prefix, EN gets `/en/...`.
  // This preserves SEO for the existing RU surface.
  localePrefix: "as-needed",
  // Use a cookie to remember explicit user choice; falls back to
  // Accept-Language when no cookie is set.
  localeCookie: {
    name: "PROSHLI_LOCALE",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 365,
  },
});

export type Locale = (typeof routing.locales)[number];
