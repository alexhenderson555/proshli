import { ArrowLeft } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Link } from "@/i18n/navigation";

export default async function NotFound() {
  const t = await getTranslations("notFound");
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
      <span className="font-mono text-6xl font-extrabold text-muted-foreground">{t("code")}</span>
      <h1 className="text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">
        {t("title")}
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">{t("subtitle")}</p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
        >
          <ArrowLeft className="h-4 w-4" />
          {t("ctaHome")}
        </Link>
        <Link
          href="/vacancies"
          className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted"
        >
          {t("ctaVacancies")}
        </Link>
      </div>
    </div>
  );
}
