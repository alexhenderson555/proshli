// Per-request next-intl configuration.
//
// Called from server components (`getTranslations`, `getMessages`, etc.)
// to resolve the active locale + load its message dictionary. The plugin
// wires this file up via `next.config.ts`.

import { hasLocale } from "next-intl";
import { getRequestConfig } from "next-intl/server";

import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  // `requestLocale` is the value the `[locale]` segment matched (a Promise).
  // For routes outside the `[locale]` segment it may be `undefined`; we
  // fall back to the configured default in that case.
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default,
  };
});
