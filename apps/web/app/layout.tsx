import type { Metadata, Viewport } from "next";
import { JetBrains_Mono, Manrope } from "next/font/google";
import "./globals.css";
import { AppHeader } from "@/components/app-header";
import { AppFooter } from "@/components/app-footer";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin", "cyrillic"],
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Otklik.ai — AI-агрегатор вакансий",
    template: "%s · Otklik.ai",
  },
  description:
    "Otklik.ai — умный поиск работы по всей России. Агрегируем вакансии с десятков площадок, фильтруем под вас и помогаем откликаться быстрее.",
  applicationName: "Otklik.ai",
  authors: [{ name: "Otklik.ai" }],
  keywords: ["работа", "вакансии", "поиск работы", "AI", "агрегатор", "Otklik"],
  openGraph: {
    type: "website",
    locale: "ru_RU",
    siteName: "Otklik.ai",
    title: "Otklik.ai — AI-агрегатор вакансий",
    description:
      "Один умный поиск по десяткам площадок. Otklik.ai находит подходящие вакансии и помогает откликаться.",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0b1220" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`${manrope.variable} ${mono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <AppHeader />
        <main className="container page-shell flex-1">{children}</main>
        <AppFooter />
      </body>
    </html>
  );
}
