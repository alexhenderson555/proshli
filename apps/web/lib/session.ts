"use client";

// localStorage key for the seeker/employer JWT. Renamed from
// `jobskout_web_token` during the Otklik.ai rebrand. We transparently
// migrate any existing session forward on first read so users don't
// get logged out.

const TOKEN_KEY = "otklik_web_token";
const LEGACY_TOKEN_KEY = "jobskout_web_token";

function migrateLegacyToken(): string | null {
  if (typeof window === "undefined") return null;
  const legacy = window.localStorage.getItem(LEGACY_TOKEN_KEY);
  if (!legacy) return null;
  try {
    window.localStorage.setItem(TOKEN_KEY, legacy);
    window.localStorage.removeItem(LEGACY_TOKEN_KEY);
  } catch {
    // storage quota / privacy mode — fall through, the legacy key still works for this session.
  }
  return legacy;
}

export function getToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(TOKEN_KEY) ?? migrateLegacyToken();
}

export function setToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(LEGACY_TOKEN_KEY);
}
