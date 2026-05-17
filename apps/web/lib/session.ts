"use client";

// Session token storage.
//
// As of Sprint 2 (F8) the backend issues the access token as an HttpOnly
// cookie (``otklik_access``) — that's the primary auth carrier and the
// browser handles it transparently. This module's localStorage shim is
// kept around for two reasons:
//
// 1. Some call sites still need to pass an explicit ``Authorization``
//    header (SSR-side fetches, the SSE streaming client which doesn't
//    re-use the fetch credentials), so we mirror the token client-side.
// 2. Backwards-compat: users with existing local storage from earlier
//    rebrand should not get bumped out on first load.
//
// Once every call site reads the cookie (or runs through a server-side
// proxy that does), this file collapses to a stub.
//
// Note: localStorage is XSS-readable; the HttpOnly cookie is the
// authoritative carrier for the security guarantee. The local mirror is
// strictly a UX convenience, NOT a security boundary.

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
  // The server-side cookie has its own expiry path — components that call
  // ``clearToken`` on logout should also hit ``api.logout()`` so the
  // browser drops ``otklik_access``. The two are wired together in the
  // header logout handler.
}
