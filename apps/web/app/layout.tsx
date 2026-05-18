// Root layout — owns <html>, <body>, fonts, theme + intl providers.
//
// We deliberately live OUTSIDE the `[locale]` segment so the root
// can be reused for every locale variant without duplicating the
// shell. `getLocale()` (next-intl) reads the locale the proxy set
// on the request, which keeps `<html lang>` in sync.

import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";

import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

// Inter Variable — Linear's typeface. Weight axis 100-900 lets us use 510 for
// body and 580 for headings without loading two static cuts. `display: swap`
// keeps the page interactive while Inter loads; the fallback chain in
// globals.css covers the cold-cache flash without visible reflow.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin", "cyrillic"],
  display: "swap",
  axes: ["opsz"],
});

const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  const t = await getTranslations({ locale, namespace: "metadata" });
  const isRu = locale === "ru";
  return {
    title: {
      default: t("titleDefault"),
      template: t("titleTemplate"),
    },
    description: t("description"),
    applicationName: "Proshli",
    authors: [{ name: "Proshli" }],
    keywords: t("keywords").split(",").map((k) => k.trim()),
    openGraph: {
      type: "website",
      locale: isRu ? "ru_RU" : "en_US",
      alternateLocale: isRu ? ["en_US"] : ["ru_RU"],
      siteName: "Proshli",
      title: t("ogTitle"),
      description: t("ogDescription"),
    },
  };
}

// Browser chrome colour. OLED uses the same `(prefers-color-scheme: dark)`
// branch since browsers don't have a separate "oled" media query; the
// chrome will fall back to the dark colour which is fine.
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0b0d" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    // `suppressHydrationWarning` is REQUIRED by next-themes — the inline
    // script that hydrates the theme runs before React, so the initial
    // server <html> may diverge from what next-themes paints client-side.
    <html
      lang={locale}
      className={`${inter.variable} ${mono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex min-h-full flex-col bg-canvas text-text-primary">
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem={false}
          themes={["dark", "light", "oled"]}
        >
          <NextIntlClientProvider locale={locale} messages={messages}>
            {children}
          </NextIntlClientProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
