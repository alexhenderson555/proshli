// Root-level 404 fallback. Reached only for paths the next-intl proxy
// matcher excludes (the localized `app/[locale]/not-found.tsx` handles
// the user-facing 404 for normal routes).
//
// We MUST NOT call `redirect("/")` here: a server-side redirect from a
// not-found page yields a 307/308 followed by a 200, which causes
// search engines to index the destination instead of recording a 404.
// Rendering directly preserves Next's automatic 404 status for this
// file and keeps the index clean.

import Link from "next/link";

export const dynamic = "force-static";

export default function GlobalNotFound() {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, sans-serif",
          display: "flex",
          minHeight: "100vh",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "1rem",
        }}
      >
        <main>
          <h1 style={{ fontSize: "2.5rem", margin: 0 }}>404</h1>
          <p style={{ marginTop: "0.5rem" }}>Page not found · Страница не найдена</p>
          <Link href="/" style={{ marginTop: "1rem", display: "inline-block" }}>
            ← Home / На главную
          </Link>
        </main>
      </body>
    </html>
  );
}
