"use client";

import { useEffect, useState } from "react";

import { Button, Card, Input, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";

export default function SeekerPage() {
  const [fullName, setFullName] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [about, setAbout] = useState("");
  const [status, setStatus] = useState("Загружаю профиль...");

  useEffect(() => {
    async function loadProfile() {
      const token = getToken();
      if (!token) {
        setStatus("Нужна авторизация во вкладке Вход.");
        return;
      }
      try {
        const profile = await api.seekerProfile(token);
        setFullName(profile.full_name);
        setTargetRole(profile.target_role);
        setLocation(profile.location);
        setSkills(profile.skills.join(", "));
        setAbout(profile.about);
        setStatus("Профиль загружен.");
      } catch (error) {
        const message = error instanceof Error ? error.message : "Не удалось загрузить профиль";
        setStatus(message);
      }
    }
    void loadProfile();
  }, []);

  async function saveProfile() {
    const token = getToken();
    if (!token) {
      setStatus("Нужна авторизация.");
      return;
    }
    try {
      await api.updateSeekerProfile(token, {
        full_name: fullName,
        target_role: targetRole,
        location,
        about,
        skills: skills
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      setStatus("Профиль сохранен.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Ошибка сохранения";
      setStatus(message);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-[1fr_340px]">
      <Card>
        <h1 className="text-xl font-extrabold">Профиль соискателя</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">
          Храни ключевые данные и управляй версиями резюме под разные роли.
        </p>
        <div className="mt-4 grid gap-2">
          <Input value={fullName} onChange={setFullName} placeholder="ФИО" />
          <Input value={targetRole} onChange={setTargetRole} placeholder="Целевая роль" />
          <Input value={location} onChange={setLocation} placeholder="Локация" />
          <Input value={skills} onChange={setSkills} placeholder="Навыки через запятую" />
          <Textarea value={about} onChange={setAbout} placeholder="О себе" rows={6} />
          <div>
            <Button onClick={saveProfile}>Сохранить профиль</Button>
          </div>
        </div>
      </Card>
      <Card>
        <h2 className="text-lg font-bold">Статус</h2>
        <p className="mt-2 text-sm text-[var(--text-muted)]">{status}</p>
        <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-alt)] p-3 text-sm text-[var(--text-muted)]">
          Раздел версии резюме уже поддерживается backend API и будет расширен отдельным конструктором в следующем
          итерационном шаге.
        </div>
      </Card>
    </div>
  );
}
