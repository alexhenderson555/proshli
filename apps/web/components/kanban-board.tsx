"use client";

// Seeker kanban — 5 horizontal lanes (saved → applied → interview →
// offer → rejected). Each lane is a column; each card is a compact
// VacancyCard projection with two arrow buttons that PATCH the row to
// the next/previous lane. Notes are inline-expandable so seekers can
// jot interview prep without leaving the dashboard.
//
// We deliberately skip drag-and-drop. dnd-kit pulls in ~30 KB gzipped
// for a 5x6 board most users will touch once a week. Arrow-button moves
// keep the bundle tight and stay touch-friendly without extra work.

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Pencil, Trash2 } from "lucide-react";

import { Badge, Button, Textarea } from "@/components/ui";
import { Link } from "@/i18n/navigation";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { ApplicationOut, ApplicationStatus } from "@/lib/types";

const LANES: ApplicationStatus[] = [
  "saved",
  "applied",
  "interview",
  "offer",
  "rejected",
];

type Props = {
  items: ApplicationOut[];
  onChange: (next: ApplicationOut) => void;
  onRemove: (id: number) => void;
};

export function KanbanBoard({ items, onChange, onRemove }: Props) {
  const t = useTranslations("dashboard");
  const locale = useLocale();
  const intlTag = locale === "ru" ? "ru-RU" : "en-US";

  // Track in-flight row id so the two buttons disable themselves without
  // freezing the whole board (other rows stay interactive).
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [openNotesId, setOpenNotesId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function laneLabel(lane: ApplicationStatus): string {
    switch (lane) {
      case "saved": return t("kanbanSaved");
      case "applied": return t("kanbanApplied");
      case "interview": return t("kanbanInterview");
      case "offer": return t("kanbanOffer");
      case "rejected": return t("kanbanRejected");
    }
  }

  function neighbour(lane: ApplicationStatus, delta: 1 | -1): ApplicationStatus | null {
    const i = LANES.indexOf(lane);
    const next = i + delta;
    if (next < 0 || next >= LANES.length) return null;
    return LANES[next] ?? null;
  }

  async function move(row: ApplicationOut, delta: 1 | -1) {
    const target = neighbour(row.status, delta);
    if (target === null) return;
    const token = getToken();
    if (!token) return;
    setPendingId(row.id);
    setError(null);
    try {
      const next = await api.updateApplication(token, row.id, { status: target });
      onChange(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("kanbanMoveError"));
    } finally {
      setPendingId(null);
    }
  }

  async function remove(row: ApplicationOut) {
    const token = getToken();
    if (!token) return;
    setPendingId(row.id);
    setError(null);
    try {
      await api.deleteApplication(token, row.id);
      onRemove(row.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("kanbanMoveError"));
    } finally {
      setPendingId(null);
    }
  }

  // Group rows by lane in a single pass so render stays O(n).
  const byLane = new Map<ApplicationStatus, ApplicationOut[]>();
  for (const lane of LANES) byLane.set(lane, []);
  for (const row of items) {
    const bucket = byLane.get(row.status as ApplicationStatus);
    if (bucket) bucket.push(row);
  }

  return (
    <div className="flex flex-col gap-2">
      {error ? (
        <p className="text-[12px] text-[var(--danger)]">{error}</p>
      ) : null}
      <div className="-mx-2 overflow-x-auto pb-2">
        <div className="flex min-w-fit gap-3 px-2">
          {LANES.map((lane) => {
            const rows = byLane.get(lane) ?? [];
            return (
              <section
                key={lane}
                className="flex w-[260px] shrink-0 flex-col gap-2 rounded border border-border bg-surface p-2"
                aria-label={laneLabel(lane)}
              >
                <header className="flex items-center justify-between px-1">
                  <span className="text-[12px] font-[580] tracking-[-0.01em] text-text-primary">
                    {laneLabel(lane)}
                  </span>
                  <span className="text-[11px] font-[510] tabular-nums text-text-tertiary">
                    {rows.length}
                  </span>
                </header>
                {rows.length === 0 ? (
                  <p className="rounded-sm border border-dashed border-border px-2 py-3 text-center text-[11px] text-text-tertiary">
                    {t("kanbanEmptyLane")}
                  </p>
                ) : (
                  rows.map((row) => {
                    const vac = row.vacancy;
                    const sourceLabel =
                      vac.source === "hh_live" ? "HH" : vac.source.toUpperCase();
                    const updated = new Date(row.updated_at).toLocaleDateString(intlTag, {
                      day: "2-digit",
                      month: "short",
                    });
                    const busy = pendingId === row.id;
                    const isNotesOpen = openNotesId === row.id;
                    const prev = neighbour(row.status, -1);
                    const next = neighbour(row.status, 1);
                    return (
                      <article
                        key={row.id}
                        className="flex flex-col gap-1.5 rounded-sm border border-border bg-elevated p-2"
                      >
                        <div className="flex items-center gap-1.5 text-text-tertiary">
                          <Badge text={sourceLabel} />
                          <span className="ml-auto text-[10px] font-[510] tabular-nums">
                            {updated}
                          </span>
                        </div>
                        <Link
                          href={`/vacancies/${vac.id}`}
                          className="block min-w-0 focus-ring"
                        >
                          <h4 className="text-[13px] font-[580] leading-snug text-text-primary hover:text-accent transition-colors line-clamp-2">
                            {vac.title}
                          </h4>
                          <p className="truncate text-[11px] text-text-secondary">
                            {vac.company}
                          </p>
                        </Link>
                        {isNotesOpen ? (
                          <NotesEditor
                            row={row}
                            onSaved={(saved) => {
                              onChange(saved);
                              setOpenNotesId(null);
                            }}
                          />
                        ) : row.notes ? (
                          <p className="text-[11px] leading-[1.4] text-text-tertiary line-clamp-3 whitespace-pre-wrap">
                            {row.notes}
                          </p>
                        ) : null}
                        <div className="mt-0.5 flex items-center justify-between gap-1">
                          <div className="flex items-center gap-0.5">
                            <button
                              type="button"
                              className="rounded-sm p-1 text-text-tertiary hover:bg-surface hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed"
                              onClick={() => move(row, -1)}
                              disabled={busy || prev === null}
                              aria-label={t("kanbanBack")}
                              title={t("kanbanBack")}
                            >
                              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
                            </button>
                            <button
                              type="button"
                              className="rounded-sm p-1 text-text-tertiary hover:bg-surface hover:text-text-primary disabled:opacity-40 disabled:cursor-not-allowed"
                              onClick={() => move(row, 1)}
                              disabled={busy || next === null}
                              aria-label={t("kanbanAdvance")}
                              title={t("kanbanAdvance")}
                            >
                              <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                            </button>
                          </div>
                          <div className="flex items-center gap-0.5">
                            <button
                              type="button"
                              className="rounded-sm p-1 text-text-tertiary hover:bg-surface hover:text-text-primary"
                              onClick={() => setOpenNotesId(isNotesOpen ? null : row.id)}
                              aria-label={t("kanbanNotesLabel")}
                              title={t("kanbanNotesLabel")}
                            >
                              <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                            </button>
                            <button
                              type="button"
                              className="rounded-sm p-1 text-text-tertiary hover:bg-surface hover:text-[var(--danger)] disabled:opacity-40 disabled:cursor-not-allowed"
                              onClick={() => remove(row)}
                              disabled={busy}
                              aria-label={t("kanbanDelete")}
                              title={t("kanbanDelete")}
                            >
                              <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                            </button>
                          </div>
                        </div>
                      </article>
                    );
                  })
                )}
              </section>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function NotesEditor({
  row,
  onSaved,
}: {
  row: ApplicationOut;
  onSaved: (saved: ApplicationOut) => void;
}) {
  const t = useTranslations("dashboard");
  const [value, setValue] = useState(row.notes);
  const [saving, setSaving] = useState(false);

  async function submit() {
    const token = getToken();
    if (!token) return;
    setSaving(true);
    try {
      const next = await api.updateApplication(token, row.id, { notes: value });
      onSaved(next);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <Textarea
        value={value}
        onChange={setValue}
        placeholder={t("kanbanNotesPlaceholder")}
        rows={3}
        className="text-[11px] leading-[1.45]"
      />
      <Button size="sm" onClick={submit} disabled={saving}>
        {saving ? t("kanbanNotesSaving") : t("kanbanNotesSave")}
      </Button>
    </div>
  );
}
