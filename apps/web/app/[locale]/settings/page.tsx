"use client";

// Settings page — four stacked sections (Profile / Notifications /
// Appearance / Account). Each section has its own save button so saving
// one thing doesn't dirty the others. Notifications + Account are
// rendered as static surfaces today (backend endpoints land next);
// Profile already PUTs through `/profiles/seeker`.

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";
import { Button, Input, Select, Textarea } from "@/components/ui";
import { ThemeSwitcher } from "@/components/theme-switcher";
import { FadeIn } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { SeekerProfileOut } from "@/lib/types";

type SaveState = "idle" | "saving" | "ok" | "error";

export default function SettingsPage() {
  const t = useTranslations("settings");
  const [token, setTokenValue] = useState<string | null>(null);

  // Profile section
  const [fullName, setFullName] = useState("");
  const [targetRole, setTargetRole] = useState("");
  const [location, setLocation] = useState("");
  const [about, setAbout] = useState("");
  const [profileState, setProfileState] = useState<SaveState>("idle");
  const [profileMessage, setProfileMessage] = useState("");

  // Notifications section
  const [telegramOn, setTelegramOn] = useState(false);
  const [frequency, setFrequency] = useState("daily");
  const [notifState, setNotifState] = useState<SaveState>("idle");

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTokenValue(getToken());
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    void (async () => {
      try {
        const profile: SeekerProfileOut | null = await api
          .seekerProfile(token)
          .catch(() => null);
        if (cancelled || !profile) return;
        setFullName(profile.full_name ?? "");
        setTargetRole(profile.target_role ?? "");
        setLocation(profile.location ?? "");
        setAbout(profile.about ?? "");
      } catch {
        // ignore
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function saveProfile() {
    if (!token) return;
    setProfileState("saving");
    try {
      await api.updateSeekerProfile(token, {
        full_name: fullName,
        target_role: targetRole,
        location,
        about,
        skills: [],
      });
      setProfileState("ok");
      setProfileMessage(t("saved"));
    } catch (err) {
      setProfileState("error");
      setProfileMessage(err instanceof Error ? err.message : "Error");
    }
  }

  function saveNotifications() {
    // Backend not wired yet — surface the intent and a positive optimistic
    // ack so the section feels real. Will be swapped to PATCH /me/notify
    // once the endpoint lands.
    setNotifState("saving");
    setTimeout(() => setNotifState("ok"), 200);
  }

  if (!token) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 rounded border border-border bg-surface p-8 text-center">
        <p className="text-[14px] text-text-secondary">{t("needsAuth")}</p>
        <Link href="/auth">
          <Button size="sm">{t("ctaLogin")}</Button>
        </Link>
      </div>
    );
  }

  return (
    <FadeIn y={6} duration={0.3} immediate>
      <div className="mx-auto flex max-w-2xl flex-col gap-8 py-8">
        <header className="flex flex-col gap-1">
          <h1 className="text-[24px] font-[580] leading-tight tracking-[-0.02em] text-text-primary">
            {t("title")}
          </h1>
          <p className="text-[13px] leading-[1.55] text-text-secondary">{t("subtitle")}</p>
        </header>

        {/* Profile */}
        <section className="flex flex-col gap-3 border-b border-border pb-8">
          <div className="kicker">{t("sectionProfile")}</div>
          <div className="grid gap-2.5">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                {t("profileNameLabel")}
              </label>
              <Input
                value={fullName}
                onChange={setFullName}
                placeholder={t("profileNamePlaceholder")}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                {t("profileRoleLabel")}
              </label>
              <Input
                value={targetRole}
                onChange={setTargetRole}
                placeholder={t("profileRolePlaceholder")}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                {t("profileLocationLabel")}
              </label>
              <Input
                value={location}
                onChange={setLocation}
                placeholder={t("profileLocationPlaceholder")}
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                {t("profileAboutLabel")}
              </label>
              <Textarea
                value={about}
                onChange={setAbout}
                placeholder={t("profileAboutPlaceholder")}
                rows={4}
              />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button onClick={saveProfile} size="sm" disabled={profileState === "saving"}>
              {t("profileSave")}
            </Button>
            {profileMessage ? (
              <span
                aria-live="polite"
                className={
                  "text-[12px] " +
                  (profileState === "error"
                    ? "text-[var(--danger)]"
                    : "text-text-tertiary")
                }
              >
                {profileMessage}
              </span>
            ) : null}
          </div>
        </section>

        {/* Notifications */}
        <section className="flex flex-col gap-3 border-b border-border pb-8">
          <div className="kicker">{t("sectionNotifications")}</div>
          <label className="flex items-center justify-between gap-3 rounded border border-border bg-surface px-3 py-2.5">
            <div className="flex flex-col">
              <span className="text-[13px] font-[510] text-text-primary">
                {t("notificationsTelegramLabel")}
              </span>
              <span className="text-[12px] text-text-tertiary">
                {t("notificationsTelegramDesc")}
              </span>
            </div>
            <input
              type="checkbox"
              checked={telegramOn}
              onChange={(e) => setTelegramOn(e.target.checked)}
              className="h-4 w-4 accent-[var(--accent)]"
            />
          </label>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
              {t("notificationsFrequencyLabel")}
            </label>
            <Select
              value={frequency}
              onChange={setFrequency}
              options={[
                { value: "off", label: t("notificationsFreqOff") },
                { value: "daily", label: t("notificationsFreqDaily") },
                { value: "weekly", label: t("notificationsFreqWeekly") },
              ]}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={saveNotifications}
              size="sm"
              disabled={notifState === "saving"}
            >
              {t("notificationsSave")}
            </Button>
            {notifState === "ok" ? (
              <span className="text-[12px] text-text-tertiary">{t("saved")}</span>
            ) : null}
          </div>
        </section>

        {/* Appearance */}
        <section className="flex flex-col gap-3 border-b border-border pb-8">
          <div className="kicker">{t("sectionAppearance")}</div>
          <div className="flex items-center justify-between gap-3">
            <label className="text-[13px] text-text-secondary">
              {t("appearanceThemeLabel")}
            </label>
            <ThemeSwitcher />
          </div>
        </section>

        {/* Account */}
        <section className="flex flex-col gap-3">
          <div className="kicker">{t("sectionAccount")}</div>
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
              {t("accountEmailLabel")}
            </span>
            <span className="text-[13px] text-text-primary">—</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary" size="sm">
              {t("accountChangePassword")}
            </Button>
          </div>

          <div className="mt-4 flex flex-col gap-2 rounded border border-[var(--danger)]/30 bg-surface p-4">
            <div className="text-[12px] font-[510] uppercase tracking-[0.08em] text-[var(--danger)]">
              {t("dangerZoneTitle")}
            </div>
            <p className="text-[13px] leading-[1.55] text-text-secondary">
              {t("dangerZoneDesc")}
            </p>
            <div>
              <Button variant="danger" size="sm">
                {t("dangerZoneCta")}
              </Button>
            </div>
          </div>
        </section>
      </div>
    </FadeIn>
  );
}
