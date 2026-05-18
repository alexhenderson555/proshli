"use client";

// Auth page — single centered column, segmented tab switcher, inline
// status (no separate sidebar panel). Brand mark sits above the card so
// the form feels like its own focused surface rather than a half of a
// generic two-column layout.

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button, Input, Select } from "@/components/ui";
import { FadeIn } from "@proshli/ui";
import { api } from "@/lib/api";
import { setToken } from "@/lib/session";
import { cn } from "@/lib/cn";

type Mode = "login" | "register";

export default function AuthPage() {
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"seeker" | "employer">("seeker");
  const [status, setStatus] = useState(t("statusInitial"));
  const [phase, setPhase] = useState<"idle" | "ok" | "error">("idle");
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await api.login(email.trim(), password)
          : await api.register(email.trim(), password, role);
      setToken(data.access_token);
      setStatus(t("statusSuccess"));
      setPhase("ok");
    } catch (error) {
      const message = error instanceof Error ? error.message : tCommon("errorUnknown");
      setStatus(`${t("statusErrorPrefix")}: ${message}`);
      setPhase("error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <FadeIn y={16} duration={0.4} immediate>
      <div className="mx-auto flex max-w-[400px] flex-col gap-5 py-8">
        {/* Brand mark + tagline */}
        <div className="flex flex-col items-center gap-2 text-center">
          <div
            className="flex h-9 w-9 items-center justify-center rounded bg-accent text-white"
            aria-hidden="true"
          >
            <span className="text-[15px] font-[580]">P</span>
          </div>
          <h1 className="text-[22px] font-[580] leading-tight tracking-[-0.02em] text-text-primary">
            {t("title")}
          </h1>
          <p className="text-[13px] leading-[1.5] text-text-secondary">{t("subtitle")}</p>
        </div>

        <section className="rounded border border-border bg-surface p-5">
          {/* Segmented tab switcher */}
          <div
            className="grid grid-cols-2 gap-0.5 rounded bg-elevated p-0.5"
            role="tablist"
            aria-label={t("title")}
          >
            {(["login", "register"] as const).map((value) => (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={mode === value}
                onClick={() => setMode(value)}
                className={cn(
                  "rounded-sm px-3 py-1.5 text-[12px] font-[510] uppercase tracking-[0.08em] transition-colors",
                  mode === value
                    ? "bg-surface text-text-primary border border-border"
                    : "text-text-tertiary hover:text-text-secondary",
                )}
              >
                {value === "login" ? t("tabLogin") : t("tabRegister")}
              </button>
            ))}
          </div>

          <div className="mt-4 flex flex-col gap-2.5">
            <Input
              value={email}
              onChange={setEmail}
              placeholder={t("emailPlaceholder")}
              type="email"
            />
            <Input
              value={password}
              onChange={setPassword}
              placeholder={t("passwordPlaceholder")}
              type="password"
            />
            {mode === "register" ? (
              <Select
                value={role}
                onChange={(value) => setRole(value as "seeker" | "employer")}
                options={[
                  { value: "seeker", label: t("roleSeeker") },
                  { value: "employer", label: t("roleEmployer") },
                ]}
              />
            ) : null}
            <Button onClick={onSubmit} disabled={loading} className="mt-1 w-full">
              {loading
                ? t("buttonLoading")
                : mode === "login"
                  ? t("buttonLogin")
                  : t("buttonRegister")}
            </Button>
            <p
              aria-live="polite"
              className={cn(
                "mt-1 text-[12px] leading-[1.5]",
                phase === "error"
                  ? "text-[var(--danger)]"
                  : phase === "ok"
                    ? "text-accent"
                    : "text-text-tertiary",
              )}
            >
              {status}
            </p>
          </div>
        </section>

        {/* Quiet helper notes — no boxed sidebar */}
        <ul className="flex flex-col gap-1.5 text-[12px] leading-[1.5] text-text-tertiary">
          <li>· {t("stateNote1")}</li>
          <li>· {t("stateNote2")}</li>
          <li>· {t("stateNote3")}</li>
        </ul>
      </div>
    </FadeIn>
  );
}
