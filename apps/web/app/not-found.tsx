// Root-level 404 fallback. Triggered for paths the next-intl middleware
// cannot rewrite (e.g. malformed locale prefixes). The localized version
// lives at `app/[locale]/not-found.tsx`; this one is intentionally
// minimal because we don't have a locale to render strings for.

import { redirect } from "next/navigation";

export default function RootNotFound() {
  // Defer to the default-locale 404 page; the localized version handles
  // the actual user-facing copy.
  redirect("/");
}
