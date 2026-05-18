// Next.js 16 Proxy (formerly known as Middleware) — locale negotiation.
//
// On every request, `createMiddleware` decides which locale should serve
// the response by combining (in order):
//   1. URL prefix (e.g. `/en/...`),
//   2. the `PROSHLI_LOCALE` cookie (set by the language switcher),
//   3. the browser's Accept-Language header.
//
// Even though the next-intl factory is still called `createMiddleware`,
// it returns a plain `(NextRequest) => NextResponse` function — exactly
// what Next 16's Proxy convention expects.  See
// `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md`.
//
// The matcher skips static assets, Next internals, the favicon, and the
// API surface so authenticated JWT calls from the SPA are never rewritten.

import createMiddleware from "next-intl/middleware";

import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Match everything except:
  //   - /api/*           (backend / route handlers)
  //   - /_next/*         (Next.js internals)
  //   - any file with a dot in the last path segment (assets like
  //     favicon.ico, robots.txt, /public/* images, source maps, etc.)
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
