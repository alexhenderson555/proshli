"use client";

// 4-way theme switcher: system / light / dark / oled.
//
// Uses the canonical next-themes `mounted` pattern: we render a stable
// placeholder server-side and on the first client paint, then flip in
// the real `<select>` once we know the active theme. Without this, the
// `value=` of the select would not match between SSR and the first
// client render, triggering a hydration mismatch.
//
// next-themes already persists the choice in localStorage and toggles
// the `class` attribute on <html> via the ThemeProvider in app/layout.

import { useEffect, useState } from "react";
import { Monitor, Moon, Sun, Zap } from "lucide-react";
import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";

const ICONS = {
  system: Monitor,
  light: Sun,
  dark: Moon,
  oled: Zap,
} as const;

type ThemeKey = keyof typeof ICONS;

const THEME_ORDER: ThemeKey[] = ["system", "light", "dark", "oled"];

export function ThemeSwitcher() {
  const t = useTranslations("header");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Defer first paint of the controlled value until we know the
  // stored / resolved theme — otherwise React 19 will refuse to hydrate.
  // This is the canonical next-themes pattern; the rule's docs carve
  // out hydration gates like this as the intended exception.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        aria-hidden="true"
        className="h-9 w-9 rounded-lg border border-border bg-card"
      />
    );
  }

  const current = (theme && THEME_ORDER.includes(theme as ThemeKey)
    ? (theme as ThemeKey)
    : "system");
  const Icon = ICONS[current];

  const labels: Record<ThemeKey, string> = {
    system: t("themeSystem"),
    light: t("themeLight"),
    dark: t("themeDark"),
    oled: t("themeOled"),
  };

  return (
    <label className="relative inline-flex h-9 items-center rounded-lg border border-border bg-card pl-2 pr-1 text-xs font-semibold text-muted-foreground">
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span className="sr-only">{t("themeAriaLabel")}</span>
      <select
        aria-label={t("themeAriaLabel")}
        value={current}
        onChange={(event) => setTheme(event.target.value)}
        className="ml-1 cursor-pointer appearance-none bg-transparent pr-4 text-xs font-semibold uppercase tracking-wider text-foreground focus:outline-none"
      >
        {THEME_ORDER.map((key) => (
          <option key={key} value={key}>
            {labels[key]}
          </option>
        ))}
      </select>
    </label>
  );
}
