// Locale segment layout.
//
// All public pages live under `app/[locale]/...`. This layout's job is to:
//   1. Validate the locale param against `routing.locales` (404 on miss).
//   2. Call `setRequestLocale` so server components rendered downstream
//      get the right locale (important for static rendering / RSC cache).
//   3. Render the page shell (header / main / footer). We deliberately
//      keep `<html>` and `<body>` in the *root* layout so theme &
//      next-intl providers wrap every route consistently.

import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";

import { AppFooter } from "@/components/app-footer";
import { AppHeader } from "@/components/app-header";
import { routing } from "@/i18n/routing";

// Statically render both locales — none of the page tree needs runtime
// locale-dependent data, so we can pre-generate per-locale variants.
export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }

  // Make the segment locale visible to downstream `getTranslations()`
  // and friends. Required for static rendering of localized routes.
  setRequestLocale(locale);

  return (
    <>
      <AppHeader />
      <main className="container page-shell flex-1">{children}</main>
      <AppFooter />
    </>
  );
}
