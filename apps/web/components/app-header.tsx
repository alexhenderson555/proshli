"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/vacancies", label: "Вакансии" },
  { href: "/seeker", label: "Соискатель" },
  { href: "/employer", label: "Работодатель" },
  { href: "/auth", label: "Вход" },
];

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-white/95 backdrop-blur">
      <div className="container flex items-center justify-between gap-4 py-3">
        <Link href="/vacancies" className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--brand)] text-white">
            JS
          </span>
          <div className="leading-tight">
            <div className="text-sm font-extrabold tracking-wide">JobSkout</div>
            <div className="text-xs text-[var(--text-muted)]">Smart Job Discovery</div>
          </div>
        </Link>
        <nav className="flex flex-wrap items-center gap-1">
          {links.map((link) => {
            const active = pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${
                  active ? "bg-[var(--brand)] text-white" : "text-[var(--text-muted)] hover:bg-[var(--surface-alt)]"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
