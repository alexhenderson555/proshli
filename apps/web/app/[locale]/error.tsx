"use client";

// Global error boundary for the App Router. Catches anything that escapes
// a nested boundary or a Server Component render error.
//
// We deliberately keep this client-side and minimal — the heavier
// telemetry path is Sentry on the API side; the frontend just needs to
// show a friendly screen and offer a recovery path.

import { useEffect } from "react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("error");
  useEffect(() => {
    // Surface to the console so it shows up in dev tools / Sentry's
    // browser SDK (once wired). `digest` is Next's correlation id.
    console.error("[otklik] unhandled client error", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
      <span className="rounded-full bg-destructive/10 px-3 py-1 text-xs font-semibold uppercase tracking-wider text-destructive">
        {t("kicker")}
      </span>
      <h1 className="text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">
        {t("title")}
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">{t("subtitle")}</p>
      {error.digest ? (
        <p className="text-xs text-muted-foreground">
          {t("errorId")}: <code className="font-mono">{error.digest}</code>
        </p>
      ) : null}
      <div className="flex gap-3">
        <button
          type="button"
          onClick={reset}
          className="rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
        >
          {t("buttonRetry")}
        </button>
        <Link
          href="/"
          className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted"
        >
          {t("buttonHome")}
        </Link>
      </div>
    </div>
  );
}
