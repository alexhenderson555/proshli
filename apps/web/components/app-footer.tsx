// Marketing footer. Three columns of resource links plus brand block.
// Server component — no client JS, translations via `getTranslations`.

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
        { href: "/billing", label: t("linkBilling") },
        { href: "/dashboard", label: t("linkDashboard") },
        { href: "/seeker", label: t("linkForSeeker") },
      ],
    },
    {
      title: t("groupResources"),
      links: [
        { href: "/employer", label: t("linkForEmployer") },
        { href: "/#features", label: t("linkFeatures") },
      ],
    },
    {
      title: t("groupCompany"),
      links: [
        { href: "mailto:hello@proshli.ru", label: "hello@proshli.ru" },
        { href: "https://t.me/proshli_ru", label: "Telegram" },
      ],
    },
  ] as const;

  return (
    <footer className="mt-16 border-t border-border bg-surface">
      <div className="container grid gap-10 py-10 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span
              className="inline-flex h-6 w-6 items-center justify-center rounded-sm bg-accent text-white text-[12px] font-[580] leading-none"
              aria-hidden="true"
            >
              P
            </span>
            <span className="text-[13px] font-[580] tracking-[-0.02em] text-text-primary">
              Proshli
            </span>
          </div>
          <p className="max-w-sm text-[13px] leading-[1.55] text-text-secondary">
            {t("tagline")}
          </p>
        </div>
        {linkGroups.map((group) => (
          <div key={group.title} className="flex flex-col gap-2.5">
            <div className="text-[10px] font-[510] uppercase tracking-[0.12em] text-text-tertiary">
              {group.title}
            </div>
            <ul className="flex flex-col gap-1.5 text-[13px]">
              {group.links.map((l) => {
                const isExternal =
                  l.href.startsWith("mailto:") ||
                  l.href.startsWith("http") ||
                  l.href.startsWith("#") ||
                  l.href.includes("#");
                return (
                  <li key={`${group.title}-${l.href}`}>
                    {isExternal ? (
                      <a
                        href={l.href}
                        className="text-text-secondary transition-colors hover:text-text-primary"
                      >
                        {l.label}
                      </a>
                    ) : (
                      <Link
                        href={l.href}
                        className="text-text-secondary transition-colors hover:text-text-primary"
                      >
                        {l.label}
                      </Link>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-border">
        <div className="container flex flex-col items-start justify-between gap-2 py-4 text-[11px] font-[510] text-text-tertiary sm:flex-row sm:items-center">
          <span>{t("copyright", { year })}</span>
          <span>{t("version")}</span>
        </div>
      </div>
    </footer>
  );
}
