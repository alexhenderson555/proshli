"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Bot, Loader2, Send, ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@proshli/ui-v2";
import { Button, Textarea } from "@/components/ui";
import { streamAiChat, type AiStreamEvent } from "@/features/ai-chat/ai-stream";
import { getToken } from "@/lib/session";
import { cn } from "@/lib/cn";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  filters?: Array<{ key: string; value: string }>;
  suggestions?: string[];
};

export function AiPanel() {
  const t = useTranslations("aiChat");
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [status, setStatus] = useState<string>("");
  const [phase, setPhase] = useState<"idle" | "streaming" | "done" | "error">("idle");
  const [usage, setUsage] = useState<{ used_today: number; limit: number } | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const filterLabelMap: Record<string, string> = {
    work_mode: t("filterWorkMode"),
    level: t("filterLevel"),
    stack: t("filterStack"),
    location: t("filterLocation"),
  };

  const filterLabel = (key: string, value: string): string => {
    return `${filterLabelMap[key] ?? key}: ${value}`;
  };

  // Toggle panel with Cmd+J or Ctrl+J
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "j" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const onEvent = useCallback((event: AiStreamEvent) => {
    switch (event.type) {
      case "status":
        setStatus(event.message);
        if (event.phase === "done") {
          setPhase("done");
        }
        break;
      case "filter":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || last.role !== "assistant") return prev;
          
          const filters = last.filters ?? [];
          const exists = filters.some((f) => f.key === event.key);
          const nextFilters = exists
            ? filters.map((f) => (f.key === event.key ? { key: event.key, value: event.value } : f))
            : [...filters, { key: event.key, value: event.value }];
            
          return [
            ...prev.slice(0, -1),
            { ...last, filters: nextFilters },
          ];
        });
        break;
      case "suggestion":
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (!last || last.role !== "assistant") return prev;
          
          const suggestions = last.suggestions ?? [];
          const nextSuggestions = suggestions.includes(event.text)
            ? suggestions
            : [...suggestions, event.text];
            
          return [
            ...prev.slice(0, -1),
            { ...last, suggestions: nextSuggestions },
          ];
        });
        break;
      case "usage":
        setUsage({ used_today: event.used_today, limit: event.limit });
        break;
      case "error":
        setStatus(event.message);
        setPhase("error");
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${crypto.randomUUID()}`,
            role: "assistant",
            content: `Ошибка: ${event.message}`,
          },
        ]);
        break;
    }
  }, []);

  const sendMessage = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed) return;

    const token = getToken();
    if (!token) {
      setMessages((prev) => [
        ...prev,
        { id: `err-auth-${crypto.randomUUID()}`, role: "assistant", content: t("statusNeedsAuth") },
      ]);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Add user message
    const userMsgId = `user-${crypto.randomUUID()}`;
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", content: trimmed },
    ]);
    setInput("");

    // Setup placeholder for assistant response
    const assistantMsgId = `assistant-${crypto.randomUUID()}`;
    setMessages((prev) => [
      ...prev,
      { id: assistantMsgId, role: "assistant", content: "" },
    ]);

    setStatus("Соединение...");
    setPhase("streaming");

    try {
      await streamAiChat(token, trimmed, {
        onEvent: (event) => {
          onEvent(event);
          if (event.type === "status" && event.phase === "composing") {
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (!last || last.role !== "assistant") return prev;
              return [
                ...prev.slice(0, -1),
                { ...last, content: event.message },
              ];
            });
          }
        },
        onDone: () => {
          setPhase((current) => (current === "error" ? current : "done"));
          setStatus("");
        },
        signal: controller.signal,
      });
    } catch (error) {
      if (controller.signal.aborted) return;
      const errMsg = error instanceof Error ? error.message : t("statusFailure");
      setStatus(errMsg);
      setPhase("error");
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== "assistant") return prev;
        return [
          ...prev.slice(0, -1),
          { ...last, content: `Ошибка: ${errMsg}` },
        ];
      });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phase === "streaming" || !input.trim()) return;
    void sendMessage(input);
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetContent side="right" className="w-full sm:max-w-md md:max-w-lg p-0 flex flex-col h-full bg-surface border-l border-border select-none">
        <SheetHeader className="flex items-center justify-between px-4 py-3.5 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded bg-accent/10 text-accent">
              <Bot className="h-4 w-4" />
            </div>
            <SheetTitle className="text-[14px] font-semibold text-text-primary">
              AI Assistant
            </SheetTitle>
          </div>
          {usage && (
            <span className="text-[11px] font-[510] tabular-nums text-text-tertiary">
              Лимит: {usage.used_today}/{usage.limit}
            </span>
          )}
        </SheetHeader>

        {/* Messages list */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 space-y-3">
              <Bot className="h-8 w-8 text-text-tertiary animate-pulse" />
              <p className="text-[13px] text-text-secondary max-w-xs">
                Задай любой вопрос по поиску вакансий или опиши резюме, чтобы я помог найти совпадения.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex flex-col max-w-[85%] rounded-lg p-3 text-[13px] leading-relaxed",
                msg.role === "user"
                  ? "bg-accent/10 text-text-primary self-end ml-auto"
                  : "bg-elevated text-text-secondary self-start border border-border/40 mr-auto"
              )}
            >
              {msg.role === "assistant" && msg.content === "" && phase === "streaming" ? (
                <div className="flex items-center gap-2 text-text-tertiary">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Думаю...</span>
                </div>
              ) : (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              )}

              {/* Dynamic filters */}
              {msg.filters && msg.filters.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-border/20 flex flex-wrap gap-1">
                  {msg.filters.map((f) => (
                    <span
                      key={f.key}
                      className="inline-flex items-center rounded-sm bg-surface border border-border px-1.5 py-0.5 text-[10px] text-text-tertiary"
                    >
                      {filterLabel(f.key, f.value)}
                    </span>
                  ))}
                </div>
              )}

              {/* Suggestions */}
              {msg.suggestions && msg.suggestions.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-border/20 space-y-1.5">
                  {msg.suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => void sendMessage(s)}
                      className="flex items-center justify-between w-full text-left rounded bg-surface hover:bg-elevated border border-border px-2 py-1.5 text-[11px] text-text-secondary hover:text-text-primary transition-colors group"
                    >
                      <span>{s}</span>
                      <ArrowRight className="h-3 w-3 text-text-tertiary group-hover:translate-x-0.5 group-hover:text-accent transition-transform" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input box */}
        <form onSubmit={handleSubmit} className="p-3 border-t border-border bg-surface">
          <div className="relative flex items-end">
            <Textarea
              value={input}
              onChange={setInput}
              placeholder="Спроси меня про вакансии..."
              rows={2}
              className="w-full resize-none pr-10 py-2 bg-elevated border border-border rounded-md text-[13px] text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-accent transition-all"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <Button
              type="submit"
              disabled={phase === "streaming" || !input.trim()}
              size="sm"
              className="absolute right-1.5 bottom-1.5 h-7 w-7 p-0 flex items-center justify-center rounded-md bg-accent hover:bg-accent-hover text-white disabled:opacity-50"
            >
              {phase === "streaming" ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
          {status && (
            <p className="mt-1.5 text-[11px] text-text-tertiary text-center">
              {status}
            </p>
          )}
        </form>
      </SheetContent>
    </Sheet>
  );
}
