// SSE client for `/ai/chat/stream`.
//
// We can't use `EventSource` here because EventSource is GET-only and our
// endpoint is POST (we need to send the message body + Authorization
// header). Instead we use `fetch` + a manual ReadableStream parser. The
// shape of the frames we accept is fixed by the backend:
//
//     event: data-status
//     data: {"phase":"gating","message":"..."}
//
// Frames are separated by a blank line. We tolerate `\r\n` and `\n`.

import { env } from "@/lib/env";

export type AiStreamEvent =
  | { type: "status"; phase: "gating" | "extracting" | "composing" | "done"; message: string }
  | { type: "filter"; key: string; value: string }
  | { type: "suggestion"; text: string }
  | { type: "usage"; used_today: number; limit: number }
  | { type: "error"; code: string; message: string };

const EVENT_TO_TYPE: Record<string, AiStreamEvent["type"] | "done"> = {
  "data-status": "status",
  "data-filter": "filter",
  "data-suggestion": "suggestion",
  "data-usage": "usage",
  "data-error": "error",
  "data-done": "done",
};

type AiStreamHandlers = {
  onEvent: (event: AiStreamEvent) => void;
  onDone?: () => void;
  signal?: AbortSignal;
};

export async function streamAiChat(
  token: string,
  message: string,
  handlers: AiStreamHandlers,
): Promise<void> {
  const resp = await fetch(`${env.NEXT_PUBLIC_API_URL}/ai/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ message }),
    signal: handlers.signal,
  });

  if (!resp.ok || !resp.body) {
    // Try to surface server-side detail as a synthetic error frame so the
    // caller has a single code path.
    let detail = `HTTP ${resp.status}`;
    try {
      const text = await resp.text();
      detail = text.slice(0, 500) || detail;
    } catch {
      // keep default
    }
    handlers.onEvent({ type: "error", code: "http_error", message: detail });
    handlers.onDone?.();
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let done = false;

  // Helper — parse and dispatch any complete frames currently in `buffer`.
  // Frames are separated by a blank line (`\n\n`).
  const drain = (final: boolean) => {
    const parts = buffer.split(/\r?\n\r?\n/);
    // Keep the last (possibly incomplete) chunk in the buffer unless we're
    // finalising — at EOF, anything left is its own frame.
    buffer = final ? "" : (parts.pop() ?? "");

    for (const raw of parts) {
      if (!raw.trim()) continue;
      let event = "";
      let data = "";
      for (const line of raw.split(/\r?\n/)) {
        if (line.startsWith("event:")) {
          event = line.slice("event:".length).trim();
        } else if (line.startsWith("data:")) {
          // Multi-line `data:` payloads are concatenated with `\n` per spec.
          const chunk = line.slice("data:".length).trim();
          data = data ? `${data}\n${chunk}` : chunk;
        }
      }
      const mapped = EVENT_TO_TYPE[event];
      if (!mapped) continue;
      if (mapped === "done") {
        handlers.onDone?.();
        done = true;
        continue;
      }
      try {
        const payload = data ? JSON.parse(data) : {};
        handlers.onEvent({ type: mapped, ...payload } as AiStreamEvent);
      } catch {
        // Malformed frame — skip rather than crash the stream.
      }
    }
  };

  try {
    while (!done) {
      const { value, done: readerDone } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: !readerDone });
        drain(false);
      }
      if (readerDone) {
        drain(true);
        if (!done) handlers.onDone?.();
        break;
      }
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // ignored — reader may already be released by abort
    }
  }
}
