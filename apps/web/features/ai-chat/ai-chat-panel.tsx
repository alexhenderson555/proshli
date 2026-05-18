"use client";

// Embedded AI search demo — flat editorial card, no gradient blobs.
// Streams typed `data-*` events from `/ai/chat/stream` and renders them
// as live status + filter chips + suggestion list — no waiting for the
// full response.
//
// When the user is not signed in we still let them *try* the surface,
// but the submit call gracefully falls back to a "log in to continue"
// hint instead of firing a request.

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Bot, Loader2, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button, Textarea } from "@/components/ui";
import { cn } from "@/lib/cn";
import { getToken } from "@/lib/session";
import { streamAiChat, type AiStreamEvent } from "@/features/ai-chat/ai-stream";

type Filter = { key: string; value: string };

export function AiChatPanel({
  className,
  placeholder,
}: {
  className?: string;
  placeholder?: string;
}) {
  const t = useTranslations("aiChat");
  const filterLabelMap: Record<string, string> = {
    work_mode: t("filterWorkMode"),
    level: t("filterLevel"),
    stack: t("filterStack"),
    location: t("filterLocation"),
  };

  function filterLabel(f: Filter): string {
    return `${filterLabelMap[f.key] ?? f.key}: ${f.value}`;
  }

  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string>(t("statusIdle"));
  const [phase, setPhase] = useState<"idle" | "streaming" | "done" | "error">("idle");
  const [filters, setFilters] = useState<Filter[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [usage, setUsage] = useState<{ used_today: number; limit: number } | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Cancel any in-flight stream on unmount — prevents the parser from
  // touching a stale closure if the user navigates away mid-stream.
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const onEvent = useCallback((event: AiStreamEvent) => {
    switch (event.type) {
      case "status":
        setStatus(event.message);
        if (event.phase === "done") setPhase("done");
        break;
      case "filter":
        setFilters((prev) =>
          prev.some((f) => f.key === event.key)
            ? prev.map((f) => (f.key === event.key ? { key: event.key, value: event.value } : f))
            : [...prev, { key: event.key, value: event.value }],
        );
        break;
      case "suggestion":
        setSuggestions((prev) => (prev.includes(event.text) ? prev : [...prev, event.text]));
        break;
      case "usage":
        setUsage({ used_today: event.used_today, limit: event.limit });
        break;
      case "error":
        setStatus(event.message);
        setPhase("error");
        break;
    }
  }, []);

  async function submit() {
    const trimmed = message.trim();
    if (!trimmed) {
      setStatus(t("statusNeedsQuery"));
      return;
    }
    const token = getToken();
    if (!token) {
      setStatus(t("statusNeedsAuth"));
      setPhase("error");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setFilters([]);
    setSuggestions([]);
    setStatus(t("statusConnecting"));
    setPhase("streaming");

    try {
      await streamAiChat(token, trimmed, {
        onEvent,
        onDone: () => {
          setPhase((current) => (current === "error" ? current : "done"));
        },
        signal: controller.signal,
      });
    } catch (error) {
      if (controller.signal.aborted) return;
      setStatus(error instanceof Error ? error.message : t("statusFailure"));
      setPhase("error");
    }
  }

  const streaming = phase === "streaming";

  return (
    <section
      className={cn(
        "rounded border border-border bg-surface p-5",
        className,
      )}
    >
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <Bot className="h-3.5 w-3.5 text-text-tertiary" aria-hidden="true" />
          <span className="kicker">{t("kicker")}</span>
        </div>
        {usage ? (
          <span className="text-[11px] font-[510] tabular-nums text-text-tertiary">
            {usage.used_today}/{usage.limit} {t("usageSuffix")}
          </span>
        ) : null}
      </header>

      <div className="mt-4 flex flex-col gap-2.5">
        <Textarea
          value={message}
          onChange={setMessage}
          placeholder={placeholder ?? t("placeholder")}
          rows={3}
          aria-label={t("ariaLabel")}
        />
        <div className="flex items-center justify-between gap-3">
          <Button onClick={submit} disabled={streaming} size="sm">
            {streaming ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                {t("buttonStreaming")}
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                {t("buttonSubmit")}
              </>
            )}
          </Button>
          <span
            className={cn(
              "text-[12px]",
              phase === "error" ? "text-[var(--danger)]" : "text-text-tertiary",
            )}
            aria-live="polite"
          >
            {status}
          </span>
        </div>
      </div>

      {filters.length > 0 ? (
        <div className="mt-5">
          <div className="kicker">{t("filtersHeader")}</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {filters.map((f) => (
              <span
                key={f.key}
                className="inline-flex items-center gap-1 rounded-sm border border-border bg-elevated px-1.5 py-px text-[11px] font-[510] text-text-secondary"
              >
                {filterLabel(f)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {suggestions.length > 0 ? (
        <div className="mt-5">
          <div className="kicker">{t("suggestionsHeader")}</div>
          <ul className="mt-2 flex flex-col gap-1">
            {suggestions.map((hint) => (
              <li key={hint}>
                <button
                  type="button"
                  onClick={() => setMessage(hint)}
                  className="group flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-[13px] text-text-secondary transition-colors hover:bg-elevated hover:text-text-primary"
                >
                  <span>{hint}</span>
                  <ArrowRight className="h-3 w-3 text-text-tertiary transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
