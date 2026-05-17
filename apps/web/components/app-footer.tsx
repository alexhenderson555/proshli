// Marketing footer. Keeps the brand mark, a few resource links, and
// legal text. Server component — no client JS needed, translations come
// via `getTranslations`.

import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

export async function AppFooter() {
  const t = await getTranslations("footer");
  const year = new Date().getFullYear();

  const linkGroups = [
    {
      title: t("groupProduct"),
      links: [
        { href: "/vacancies", label: t("linkCatalog") },
        { href: "/seeker", label: t("linkForSeeker") },
        { href: "/employer", label: t("linkForEmployer") },
      ],
    },
    {
      title: t("groupCompany"),
      links: [
        { href: "/#features", label: t("linkFeatures") },
        { href: "mailto:hello@otklik.ai", label: "hello@otklik.ai" },
      ],
    },
  ] as const;

  return (
    <footer className="mt-12 border-t border-border bg-card">
      <div className="container grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr]">
        <div className="flex flex-col gap-3">
          <div className="text-base font-extrabold tracking-tight">Otklik.ai</div>
          <p className="max-w-sm text-sm text-muted-foreground">{t("tagline")}</p>
        </div>
        {linkGroups.map((group) => (
          <div key={group.title} className="flex flex-col gap-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {group.title}
            </div>
            <ul className="flex flex-col gap-1.5 text-sm">
              {group.links.map((l) => (
                <li key={`${group.title}-${l.href}`}>
                  {l.href.startsWith("mailto:") || l.href.startsWith("#") || l.href.includes("#") ? (
                    <a href={l.href} className="text-foreground transition hover:text-primary">
                      {l.label}
                    </a>
                  ) : (
                    <Link href={l.href} className="text-foreground transition hover:text-primary">
                      {l.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border">
        <div className="container flex flex-col items-start justify-between gap-2 py-4 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <span>{t("copyright", { year })}</span>
          <span>{t("version")}</span>
        </div>
      </div>
    </footer>
  );
}
