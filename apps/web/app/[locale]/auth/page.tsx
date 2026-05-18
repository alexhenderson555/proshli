"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button, Card, Input, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { setToken } from "@/lib/session";

type Mode = "login" | "register";

export default function AuthPage() {
  const t = useTranslations("auth");
  const tCommon = useTranslations("common");
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"seeker" | "employer">("seeker");
  const [status, setStatus] = useState(t("statusInitial"));
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
    } catch (error) {
      const message = error instanceof Error ? error.message : tCommon("errorUnknown");
      setStatus(`${t("statusErrorPrefix")}: ${message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
      <Card>
        <h1 className="text-2xl font-extrabold">{t("title")}</h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
        <div className="mt-4 grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <Button variant={mode === "login" ? "primary" : "secondary"} onClick={() => setMode("login")}>
              {t("tabLogin")}
            </Button>
            <Button variant={mode === "register" ? "primary" : "secondary"} onClick={() => setMode("register")}>
              {t("tabRegister")}
            </Button>
          </div>
          <Input value={email} onChange={setEmail} placeholder={t("emailPlaceholder")} type="email" />
          <Input value={password} onChange={setPassword} placeholder={t("passwordPlaceholder")} type="password" />
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
          <Button onClick={onSubmit} disabled={loading}>
            {loading ? t("buttonLoading") : mode === "login" ? t("buttonLogin") : t("buttonRegister")}
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-bold">{t("stateTitle")}</h2>
        <p className="mt-2 rounded-xl bg-[var(--surface-alt)] p-3 text-sm text-[var(--text-muted)]">{status}</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[var(--text-muted)]">
          <li>{t("stateNote1")}</li>
          <li>{t("stateNote2")}</li>
          <li>{t("stateNote3")}</li>
        </ul>
      </Card>
    </div>
  );
}
