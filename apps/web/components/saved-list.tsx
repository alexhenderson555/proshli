"use client";

// Saved-vacancies list (kanban "saved" lane projected as a flat feed).
// Each row borrows the VacancyCard idiom but adds two seeker actions —
// "Move to Applications" (advance status to "applied") and "Unsave"
// (hard delete the application row). State is owned by the parent so
// the overview-tab counts stay in sync without a refetch.

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { Badge, Button } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { ApplicationOut } from "@/lib/types";

type Props = {
  items: ApplicationOut[];
  onAdvance: (next: ApplicationOut) => void;
  onRemove: (id: number) => void;
};

export function SavedList({ items, onAdvance, onRemove }: Props) {
  const t = useTranslations("dashboard");
  const locale = useLocale();
  const intlTag = locale === "ru" ? "ru-RU" : "en-US";
  const [pendingId, setPendingId] = useState<number | null>(null);

  async function advance(row: ApplicationOut) {
    const token = getToken();
    if (!token) return;
    setPendingId(row.id);
    try {
      const next = await api.updateApplication(token, row.id, { status: "applied" });
      onAdvance(next);
    } catch {
      // Swallow — parent renders error elsewhere. We just keep the row
      // in place and re-enable the buttons so the seeker can retry.
    } finally {
      setPendingId(null);
    }
  }

  async function remove(row: ApplicationOut) {
    const token = getToken();
    if (!token) return;
    setPendingId(row.id);
    try {
      await api.deleteApplication(token, row.id);
      onRemove(row.id);
    } catch {
      // ditto
    } finally {
      setPendingId(null);
    }
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col gap-2 rounded border border-border bg-surface p-6 text-center">
        <p className="text-[13px] text-text-secondary">{t("savedEmpty")}</p>
        <p className="text-[12px] text-text-tertiary">{t("savedHint")}</p>
      </div>
    );
  }

  return (
    <div className="rounded border border-border bg-surface px-4">
      {items.map((row) => {
        const vac = row.vacancy;
        const sourceLabel = vac.source === "hh_live" ? "HH" : vac.source.toUpperCase();
        const saved = new Date(row.created_at).toLocaleDateString(intlTag, {
          day: "2-digit",
          month: "short",
        });
        const busy = pendingId === row.id;
        return (
          <article
            key={row.id}
            className="border-b border-border py-3 last:border-b-0 flex items-center gap-3"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 text-text-tertiary">
                <Badge text={sourceLabel} />
                <span className="text-[11px] font-[510] tabular-nums">{saved}</span>
              </div>
              <Link href={`/vacancies/${vac.id}`} className="block min-w-0 focus-ring">
                <h3 className="truncate mt-1 text-[14px] font-[580] leading-snug tracking-[-0.01em] text-text-primary hover:text-accent transition-colors">
                  {vac.title}
                </h3>
                <p className="truncate text-[12px] text-text-secondary">
                  {vac.company}
                  <span className="mx-1.5 text-text-tertiary">·</span>
                  {vac.location}
                </p>
              </Link>
            </div>
            <div className="flex shrink-0 items-center gap-1.5">
              <Button
                size="sm"
                onClick={() => advance(row)}
                disabled={busy}
              >
                {t("savedAdvance")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => remove(row)}
                disabled={busy}
              >
                {t("savedUnsave")}
              </Button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
