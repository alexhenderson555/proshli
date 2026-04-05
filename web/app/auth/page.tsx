"use client";

import { useState } from "react";

import { Button, Card, Input, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { setToken } from "@/lib/session";

type Mode = "login" | "register";

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"seeker" | "employer">("seeker");
  const [status, setStatus] = useState("Введите данные аккаунта");
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setLoading(true);
    try {
      const data =
        mode === "login"
          ? await api.login(email.trim(), password)
          : await api.register(email.trim(), password, role);
      setToken(data.access_token);
      setStatus("Успех: токен сохранен в localStorage.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Неизвестная ошибка";
      setStatus(`Ошибка: ${message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-[1.2fr_1fr]">
      <Card>
        <h1 className="text-2xl font-extrabold">Onboarding JobSkout</h1>
        <p className="mt-2 text-sm text-[var(--text-muted)]">
          HH-похожий входной поток, но с AI-first идентичностью: создаешь аккаунт и сразу переходишь к фильтрам и
          персональному матчингу.
        </p>
        <div className="mt-4 grid gap-3">
          <div className="grid grid-cols-2 gap-2">
            <Button variant={mode === "login" ? "primary" : "secondary"} onClick={() => setMode("login")}>
              Вход
            </Button>
            <Button variant={mode === "register" ? "primary" : "secondary"} onClick={() => setMode("register")}>
              Регистрация
            </Button>
          </div>
          <Input value={email} onChange={setEmail} placeholder="you@mail.com" type="email" />
          <Input value={password} onChange={setPassword} placeholder="Пароль (min 8 символов)" type="password" />
          {mode === "register" ? (
            <Select
              value={role}
              onChange={(value) => setRole(value as "seeker" | "employer")}
              options={[
                { value: "seeker", label: "Соискатель" },
                { value: "employer", label: "Работодатель" },
              ]}
            />
          ) : null}
          <Button onClick={onSubmit} disabled={loading}>
            {loading ? "Обрабатываю..." : mode === "login" ? "Войти" : "Создать аккаунт"}
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="text-lg font-bold">Состояние</h2>
        <p className="mt-2 rounded-xl bg-[var(--surface-alt)] p-3 text-sm text-[var(--text-muted)]">{status}</p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[var(--text-muted)]">
          <li>JWT хранится в localStorage как `jobskout_web_token`.</li>
          <li>Дальше переходи в разделы `Вакансии` или `Соискатель`.</li>
          <li>Для employer-flow открой страницу `Работодатель`.</li>
        </ul>
      </Card>
    </div>
  );
}
