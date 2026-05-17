"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { Button, Card, Input, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";

export default function SeekerPage() {
  const t = useTranslations("seeker");
  const [fullName, setFullName] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [location, setLocation] = useState("");
  const [skills, setSkills] = useState("");
  const [about, setAbout] = useState("");
  const [status, setStatus] = useState(t("statusLoading"));

  useEffect(() => {
    async function loadProfile() {
      const token = getToken();
      if (!token) {
        setStatus(t("statusNeedsAuth"));
        return;
      }
      try {
        const profile = await api.seekerProfile(token);
        setFullName(profile.full_name);
        setTargetRole(profile.target_role);
        setLocation(profile.location);
        setSkills(profile.skills.join(", "));
        setAbout(profile.about);
        setStatus(t("statusLoaded"));
      } catch (error) {
        const message = error instanceof Error ? error.message : t("errorLoad");
        setStatus(message);
      }
    }
    void loadProfile();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveProfile() {
    const token = getToken();
    if (!token) {
      setStatus(t("statusNeedsAuthShort"));
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
      setStatus(t("statusSaved"));
    } catch (error) {
      const message = error instanceof Error ? error.message : t("errorSave");
      setStatus(message);
    }
  }

  return (
    <div className="grid gap-4 md:grid-cols-[1fr_340px]">
      <Card>
        <h1 className="text-xl font-extrabold">{t("title")}</h1>
        <p className="mt-1 text-sm text-[var(--text-muted)]">{t("subtitle")}</p>
        <div className="mt-4 grid gap-2">
          <Input value={fullName} onChange={setFullName} placeholder={t("fullName")} />
          <Input value={targetRole} onChange={setTargetRole} placeholder={t("targetRole")} />
          <Input value={location} onChange={setLocation} placeholder={t("location")} />
          <Input value={skills} onChange={setSkills} placeholder={t("skills")} />
          <Textarea value={about} onChange={setAbout} placeholder={t("about")} rows={6} />
          <div>
            <Button onClick={saveProfile}>{t("buttonSave")}</Button>
          </div>
        </div>
      </Card>
      <Card>
        <h2 className="text-lg font-bold">{t("stateTitle")}</h2>
        <p className="mt-2 text-sm text-[var(--text-muted)]">{status}</p>
        <div className="mt-4 rounded-xl border border-[var(--line)] bg-[var(--surface-alt)] p-3 text-sm text-[var(--text-muted)]">
          {t("stateNote")}
        </div>
      </Card>
    </div>
  );
}
