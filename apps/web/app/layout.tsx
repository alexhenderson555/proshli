import type { Metadata } from "next";
import { JetBrains_Mono, Manrope } from "next/font/google";
import "./globals.css";
import { AppHeader } from "@/components/app-header";

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin", "cyrillic"],
});

const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "JobSkout Web",
  description: "AI-powered job aggregator UI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`${manrope.variable} ${mono.variable} h-full antialiased`}>
      <body className="min-h-full">
        <AppHeader />
        <main className="container page-shell">{children}</main>
      </body>
    </html>
  );
}
