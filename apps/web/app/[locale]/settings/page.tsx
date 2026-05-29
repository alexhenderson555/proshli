"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { ShieldCheck, User, Bell, Palette, ShieldAlert } from "lucide-react";

import { Link } from "@/i18n/navigation";
import { Button, Input, Select, Textarea } from "@/components/ui";
import { ThemeSwitcher } from "@/components/theme-switcher";
import { FadeIn, Stagger } from "@proshli/ui";
import { api } from "@/lib/api";
import { getToken } from "@/lib/session";
import type { SeekerProfileOut } from "@/lib/types";
import { AppShell } from "@/components/app-shell";

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
    const t = setTimeout(() => setTokenValue(getToken()), 0);
    return () => clearTimeout(t);
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
    setNotifState("saving");
    setTimeout(() => setNotifState("ok"), 200);
  }

  if (!token) {
    return (
      <div className="relative min-h-screen flex items-center justify-center">
        <div className="absolute inset-0 bg-canvas z-0" />
        <div className="relative z-10 mx-auto flex max-w-md flex-col items-center gap-4 rounded-lg border border-border/80 bg-surface/80 backdrop-blur-md p-8 text-center shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded border border-border bg-elevated/40 text-text-tertiary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <h2 className="text-[18px] font-[600] tracking-[-0.01em] text-white">Требуется авторизация</h2>
          <p className="text-[13px] leading-[1.6] text-text-secondary">{t("needsAuth")}</p>
          <Link href="/auth">
            <Button className="px-6 py-2 bg-accent hover:bg-accent-hover text-white rounded font-medium shadow-[0_4px_16px_rgba(99,102,241,0.2)]">
              {t("ctaLogin")}
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <AppShell
      activeTab="settings"
      role="seeker"
      profileName={fullName}
      profileSubtitle={targetRole}
    >
      <FadeIn y={6} duration={0.3} immediate>
        <header className="mb-6 flex flex-col gap-1.5 border-b border-border/60 pb-5">
          <h1 className="text-[26px] font-[600] leading-tight tracking-[-0.02em] text-white">
            {t("title")}
          </h1>
          <p className="text-[13px] leading-[1.6] text-text-secondary">{t("subtitle")}</p>
        </header>
      </FadeIn>

      <Stagger step={0.05} immediate className="flex flex-col gap-6 max-w-2xl">
        {/* Profile */}
        <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
          <h2 className="text-[16px] font-[600] text-white flex items-center gap-2 mb-4">
            <User className="h-4 w-4 text-accent" /> {t("sectionProfile")}
          </h2>
          <div className="grid gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                  {t("profileNameLabel")}
                </label>
                <Input value={fullName} onChange={setFullName} placeholder={t("profileNamePlaceholder")} className="bg-surface/50 border-border/80 text-[13px]" />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                  {t("profileRoleLabel")}
                </label>
                <Input value={targetRole} onChange={setTargetRole} placeholder={t("profileRolePlaceholder")} className="bg-surface/50 border-border/80 text-[13px]" />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                {t("profileLocationLabel")}
              </label>
              <Input value={location} onChange={setLocation} placeholder={t("profileLocationPlaceholder")} className="bg-surface/50 border-border/80 text-[13px]" />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
                {t("profileAboutLabel")}
              </label>
              <Textarea value={about} onChange={setAbout} placeholder={t("profileAboutPlaceholder")} rows={4} className="bg-surface/50 border-border/80 text-[13px]" />
            </div>
            <div className="flex items-center gap-3 pt-2">
              <Button onClick={saveProfile} disabled={profileState === "saving"} className="bg-white text-black hover:bg-white/90 text-[13px] px-6">
                {t("profileSave")}
              </Button>
              {profileMessage && (
                <span className={`text-[12px] ${profileState === "error" ? "text-red-400" : "text-text-tertiary"}`}>
                  {profileMessage}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Notifications */}
        <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
          <h2 className="text-[16px] font-[600] text-white flex items-center gap-2 mb-4">
            <Bell className="h-4 w-4 text-accent" /> {t("sectionNotifications")}
          </h2>
          <div className="grid gap-4">
            <label className="flex items-center justify-between gap-3 rounded border border-border/60 bg-surface/40 px-4 py-3 cursor-pointer hover:bg-surface/60 transition-colors">
              <div className="flex flex-col">
                <span className="text-[14px] font-[510] text-white">
                  {t("notificationsTelegramLabel")}
                </span>
                <span className="text-[12px] text-text-tertiary mt-0.5">
                  {t("notificationsTelegramDesc")}
                </span>
              </div>
              <div className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75" style={{ backgroundColor: telegramOn ? 'var(--accent)' : 'var(--surface-elevated)' }}>
                <input type="checkbox" className="sr-only" checked={telegramOn} onChange={(e) => setTelegramOn(e.target.checked)} />
                <span aria-hidden="true" className={`${telegramOn ? 'translate-x-4' : 'translate-x-0'} pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out`} />
              </div>
            </label>
            <div className="flex flex-col gap-1.5">
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
            <div className="flex items-center gap-3 pt-2">
              <Button onClick={saveNotifications} disabled={notifState === "saving"} className="bg-white text-black hover:bg-white/90 text-[13px] px-6">
                {t("notificationsSave")}
              </Button>
              {notifState === "ok" && <span className="text-[12px] text-text-tertiary">{t("saved")}</span>}
            </div>
          </div>
        </div>

        {/* Appearance */}
        <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
          <h2 className="text-[16px] font-[600] text-white flex items-center gap-2 mb-4">
            <Palette className="h-4 w-4 text-accent" /> {t("sectionAppearance")}
          </h2>
          <div className="flex items-center justify-between gap-3 rounded border border-border/60 bg-surface/40 px-4 py-3">
            <label className="text-[13px] text-text-secondary">
              {t("appearanceThemeLabel")}
            </label>
            <ThemeSwitcher />
          </div>
        </div>

        {/* Account */}
        <div className="rounded-lg border border-border/80 bg-surface/30 backdrop-blur-sm p-6 shadow-[0_4px_24px_rgba(0,0,0,0.1)]">
          <h2 className="text-[16px] font-[600] text-white flex items-center gap-2 mb-4">
            <ShieldAlert className="h-4 w-4 text-accent" /> {t("sectionAccount")}
          </h2>
          <div className="flex flex-col gap-1.5 mb-6">
            <span className="text-[11px] font-[510] uppercase tracking-[0.08em] text-text-tertiary">
              {t("accountEmailLabel")}
            </span>
            <span className="text-[14px] text-white">—</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary" className="text-[13px] px-5">
              {t("accountChangePassword")}
            </Button>
          </div>

          <div className="mt-6 flex flex-col gap-3 rounded-lg border border-red-500/20 bg-red-500/5 p-5">
            <div className="text-[12px] font-[600] uppercase tracking-[0.08em] text-red-400">
              {t("dangerZoneTitle")}
            </div>
            <p className="text-[13px] leading-[1.55] text-text-secondary max-w-md">
              {t("dangerZoneDesc")}
            </p>
            <div>
              <Button variant="danger" className="text-[13px] px-5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30">
                {t("dangerZoneCta")}
              </Button>
            </div>
          </div>
        </div>
      </Stagger>
    </AppShell>
  );
}
