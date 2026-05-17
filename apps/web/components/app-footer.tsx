// Marketing footer. Keeps the brand mark, a few resource links, and
// legal text. Static — no client JS needed.

import Link from "next/link";

const linkGroups = [
  {
    title: "Продукт",
    links: [
      { href: "/vacancies", label: "Каталог вакансий" },
      { href: "/seeker", label: "Соискателю" },
      { href: "/employer", label: "Работодателю" },
    ],
  },
  {
    title: "Компания",
    links: [
      { href: "/#features", label: "Возможности" },
      { href: "mailto:hello@otklik.ai", label: "hello@otklik.ai" },
    ],
  },
];

export function AppFooter() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-12 border-t border-border bg-card">
      <div className="container grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr]">
        <div className="flex flex-col gap-3">
          <div className="text-base font-extrabold tracking-tight">Otklik.ai</div>
          <p className="max-w-sm text-sm text-muted-foreground">
            AI-агрегатор вакансий: один поиск по десяткам площадок, фильтры на естественном языке
            и доставка в Telegram.
          </p>
        </div>
        {linkGroups.map((group) => (
          <div key={group.title} className="flex flex-col gap-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {group.title}
            </div>
            <ul className="flex flex-col gap-1.5 text-sm">
              {group.links.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-foreground transition hover:text-primary">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border">
        <div className="container flex flex-col items-start justify-between gap-2 py-4 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <span>© {year} Otklik.ai · Сделано в России</span>
          <span>v0.1 · early access</span>
        </div>
      </div>
    </footer>
  );
}
