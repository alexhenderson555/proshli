"use client";

// Embedded AI search demo. Shown on the landing page and (optionally)
// inside the vacancies sidebar. Streams typed `data-*` events from
// `/ai/chat/stream` and renders them as live status + filter chips +
// suggestion list — no waiting for the full response.
//
// When the user is not signed in we still let them *try* the surface,
// but the submit call gracefully falls back to a "log in to continue"
// hint instead of firing a request.

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Bot, Loader2, Sparkles } from "lucide-react";

import { Button, Textarea } from "@/components/ui";
import { cn } from "@/lib/cn";
import { getToken } from "@/lib/session";
import { streamAiChat, type AiStreamEvent } from "@/features/ai-chat/ai-stream";

type Filter = { key: string; value: string };

const FILTER_LABEL: Record<string, string> = {
  work_mode: "Формат",
  level: "Уровень",
  stack: "Стек",
  location: "Локация",
};

function filterLabel(f: Filter): string {
  return `${FILTER_LABEL[f.key] ?? f.key}: ${f.value}`;
}

export function AiChatPanel({
  className,
  placeholder = "Например: ищу удалённого middle python разработчика от 250к",
}: {
  className?: string;
  placeholder?: string;
}) {
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<string>("Опишите идеальную вакансию своими словами.");
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
      setStatus("Сначала опишите запрос — хотя бы пару слов.");
      return;
    }
    const token = getToken();
    if (!token) {
      setStatus("Войдите в аккаунт, чтобы запустить AI-поиск.");
      setPhase("error");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setFilters([]);
    setSuggestions([]);
    setStatus("Подключаюсь к Otklik AI…");
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
      setStatus(error instanceof Error ? error.message : "Не удалось получить ответ AI.");
      setPhase("error");
    }
  }

  const streaming = phase === "streaming";

  return (
    <section className={cn("panel relative overflow-hidden p-6 lg:p-7", className)}>
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-[hsl(var(--primary)/0.08)] via-transparent to-[hsl(var(--accent)/0.08)]" />
      <header className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
          <Bot className="h-4 w-4 text-accent" aria-hidden="true" />
          Otklik AI · попробовать
        </div>
        {usage ? (
          <span className="text-xs text-muted-foreground">
            {usage.used_today}/{usage.limit} в день
          </span>
        ) : null}
      </header>

      <div className="mt-4 flex flex-col gap-3">
        <Textarea
          value={message}
          onChange={setMessage}
          placeholder={placeholder}
          rows={3}
          aria-label="Запрос для Otklik AI"
        />
        <div className="flex items-center justify-between gap-3">
          <Button onClick={submit} disabled={streaming}>
            {streaming ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Стримлю…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                Найти с AI
              </>
            )}
          </Button>
          <span
            className={cn(
              "text-sm",
              phase === "error" ? "text-destructive" : "text-muted-foreground",
            )}
            aria-live="polite"
          >
            {status}
          </span>
        </div>
      </div>

      {filters.length > 0 ? (
        <div className="mt-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Извлечённые фильтры
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {filters.map((f) => (
              <span
                key={f.key}
                className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary"
              >
                {filterLabel(f)}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {suggestions.length > 0 ? (
        <div className="mt-5">
          <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Похожие запросы
          </div>
          <ul className="mt-2 flex flex-col gap-1.5">
            {suggestions.map((hint) => (
              <li key={hint}>
                <button
                  type="button"
                  onClick={() => setMessage(hint)}
                  className="group flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm text-foreground transition hover:bg-muted"
                >
                  <span>{hint}</span>
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
