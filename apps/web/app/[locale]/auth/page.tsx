"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { KeyRound, ShieldAlert } from "lucide-react";

import { Button, Input, Select } from "@/components/ui";
import { FadeIn } from "@proshli/ui";
import { api } from "@/lib/api";
import { setToken } from "@/lib/session";
import { cn } from "@/lib/cn";
import { HeroBackdrop } from "@/components/hero-backdrop";

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
    <div className="relative min-h-screen flex items-center justify-center py-12 px-4">
      <HeroBackdrop />

      <div className="relative z-10 w-full max-w-[400px]">
        <FadeIn y={16} duration={0.4} immediate>
          <div className="flex flex-col gap-6">
            {/* Brand mark + tagline */}
            <div className="flex flex-col items-center gap-3 text-center">
              <div
                className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-white shadow-[0_4px_16px_rgba(99,102,241,0.25)]"
                aria-hidden="true"
              >
                <span className="text-[16px] font-[600]">P</span>
              </div>
              <h1 className="text-[24px] font-[600] leading-tight tracking-[-0.02em] text-white">
                {t("title")}
              </h1>
              <p className="text-[13px] leading-[1.6] text-text-secondary">{t("subtitle")}</p>
            </div>

            <section className="rounded-lg border border-border/80 bg-surface/50 backdrop-blur-md p-6 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
              {/* Segmented tab switcher */}
              <div
                className="grid grid-cols-2 gap-0.5 rounded-lg bg-elevated/40 border border-border/60 p-0.5"
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
                      "rounded px-3 py-1.5 text-[11px] font-[600] uppercase tracking-[0.1em] transition-all duration-150",
                      mode === value
                        ? "bg-white/[0.04] text-white border border-white/5 shadow-sm"
                        : "text-text-tertiary hover:text-text-secondary",
                    )}
                  >
                    {value === "login" ? t("tabLogin") : t("tabRegister")}
                  </button>
                ))}
              </div>

              <div className="mt-5 flex flex-col gap-3">
                <Input
                  value={email}
                  onChange={setEmail}
                  placeholder={t("emailPlaceholder")}
                  type="email"
                  className="bg-elevated/20 focus:border-accent/50 text-[13px]"
                />
                <Input
                  value={password}
                  onChange={setPassword}
                  placeholder={t("passwordPlaceholder")}
                  type="password"
                  className="bg-elevated/20 focus:border-accent/50 text-[13px]"
                />
                {mode === "register" ? (
                  <Select
                    value={role}
                    onChange={(value) => setRole(value as "seeker" | "employer")}
                    options={[
                      { value: "seeker", label: t("roleSeeker") },
                      { value: "employer", label: t("roleEmployer") },
                    ]}
                    className="bg-elevated/20 focus:border-accent/50 text-[13px]"
                  />
                ) : null}
                
                <Button onClick={onSubmit} disabled={loading} className="mt-1 w-full bg-accent hover:bg-accent-hover text-white py-2 rounded font-medium shadow-[0_4px_16px_rgba(99,102,241,0.2)]">
                  {loading
                    ? t("buttonLoading")
                    : mode === "login"
                      ? t("buttonLogin")
                      : t("buttonRegister")}
                </Button>
                
                <p
                  aria-live="polite"
                  className={cn(
                    "mt-2 text-[12px] leading-[1.6] flex items-center gap-1.5 justify-center border-t border-border/30 pt-2",
                    phase === "error"
                      ? "text-[var(--danger)]"
                      : phase === "ok"
                        ? "text-accent"
                        : "text-text-tertiary",
                  )}
                >
                  {phase === "error" && <ShieldAlert className="h-3.5 w-3.5" />}
                  {phase === "ok" && <KeyRound className="h-3.5 w-3.5" />}
                  {status}
                </p>
              </div>
            </section>

            {/* Quiet helper notes */}
            <ul className="flex flex-col gap-2 rounded-lg border border-border/40 bg-surface/20 p-4 text-[12px] leading-[1.6] text-text-tertiary">
              <li className="flex gap-2">
                <span className="text-accent">•</span>
                <span>{t("stateNote1")}</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent">•</span>
                <span>{t("stateNote2")}</span>
              </li>
              <li className="flex gap-2">
                <span className="text-accent">•</span>
                <span>{t("stateNote3")}</span>
              </li>
            </ul>
          </div>
        </FadeIn>
      </div>
    </div>
  );
}
