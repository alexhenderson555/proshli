"use client";

// Thin client-side wrapper around next-themes' provider so the rest of
// the app can stay server-rendered. Mounted once inside the root
// layout's <body>.
//
// We deliberately do NOT enable the `enableColorScheme` flag — next-themes
// would otherwise inject `color-scheme: light dark` on <html>, which
// fights our hand-rolled OLED token set (pitch black backgrounds).

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
