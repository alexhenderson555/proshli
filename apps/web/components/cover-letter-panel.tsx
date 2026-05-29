"use client";

// AI cover-letter inline panel on the vacancy detail page.
//
// Opens beneath the Save button. Two pickers (tone + language), a
// generate button, the resulting text in a read-only textarea-like
// block, and a copy-to-clipboard control. Counts against the same
// daily AI budget as /ai/chat — the response carries the latest
// (used_today, limit) tuple so we can warn before the user hits zero.

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { Sparkles, Copy, Check } from "lucide-react";

import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";

type Tone = "formal" | "friendly";
type Language = "ru" | "en";

type Props = {
  vacancyId: number;
};

export function CoverLetterPanel({ vacancyId }: Props) {
  const t = useTranslations("vacancies.detail");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [tone, setTone] = useState<Tone>("formal");
  const [language, setLanguage] = useState<Language>(locale === "en" ? "en" : "ru");
  const [body, setBody] = useState<string | null>(null);
  const [usage, setUsage] = useState<{ used: number; limit: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function generate() {
    const token = getToken();
    if (!token) {
      setError(t("coverLetterNeedsAuth"));
      setOpen(true);
      return;
    }
    setLoading(true);
    setError(null);
    setOpen(true);
    try {
      const res = await api.coverLetter(token, {
        vacancy_id: vacancyId,
        tone,
        language,
      });
      setBody(res.body);
      setUsage({ used: res.used_today, limit: res.limit });
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("coverLetterError");
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    if (!body) return;
    try {
      await navigator.clipboard.writeText(body);
      setCopied(true);
      // Reset the "Copied" hint shortly so the button re-arms — keeps
      // the affordance discoverable if the seeker copies multiple times.
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API can refuse in non-secure contexts; we don't try
      // to fall back to execCommand. The text is still in the textarea
      // for manual copy.
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={generate}
          disabled={loading}
          aria-expanded={open}
        >
          <Sparkles className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
          {loading ? t("coverLetterGenerating") : t("coverLetterButton")}
        </Button>
      </div>
      {open ? (
        <div className="flex flex-col gap-2 rounded border border-border bg-elevated p-3">
          <div className="flex flex-wrap items-center gap-3 text-[12px]">
            <label className="flex items-center gap-1.5 text-text-secondary">
              {t("coverLetterToneLabel")}
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value as Tone)}
                className="rounded border border-border bg-surface px-1.5 py-0.5 text-[12px] text-text-primary"
              >
                <option value="formal">{t("coverLetterToneFormal")}</option>
                <option value="friendly">{t("coverLetterToneFriendly")}</option>
              </select>
            </label>
            <label className="flex items-center gap-1.5 text-text-secondary">
              {t("coverLetterLanguageLabel")}
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as Language)}
                className="rounded border border-border bg-surface px-1.5 py-0.5 text-[12px] text-text-primary"
              >
                <option value="ru">RU</option>
                <option value="en">EN</option>
              </select>
            </label>
            {body ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={generate}
                disabled={loading}
              >
                {t("coverLetterRegenerate")}
              </Button>
            ) : null}
          </div>
          {error ? (
            <p className="text-[12px] text-[var(--danger)]">{error}</p>
          ) : null}
          {body ? (
            <>
              <div className="kicker">{t("coverLetterTitle")}</div>
              <pre className="whitespace-pre-wrap rounded border border-border bg-surface p-3 text-[13px] leading-[1.6] text-text-primary font-sans">
                {body}
              </pre>
              <div className="flex items-center justify-between gap-2">
                {usage ? (
                  <span className="text-[11px] tabular-nums text-text-tertiary">
                    {t("coverLetterUsage", {
                      used: usage.used,
                      limit: usage.limit,
                    })}
                  </span>
                ) : <span />}
                <Button variant="secondary" size="sm" onClick={copy}>
                  {copied ? (
                    <Check className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  ) : (
                    <Copy className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  {copied ? t("coverLetterCopied") : t("coverLetterCopy")}
                </Button>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
