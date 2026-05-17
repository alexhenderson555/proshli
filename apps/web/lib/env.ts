// Validated environment variables.
//
// `@t3-oss/env-nextjs` checks at boot that every variable below is set
// (or has a default) and the right shape. The build fails loud if
// something is missing, instead of `undefined` cascading into 500s at
// runtime.
//
// Server-only variables go under `server`, client-exposed under `client`
// (must be prefixed with `NEXT_PUBLIC_`).

import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

export const env = createEnv({
  server: {
    NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
    SENTRY_AUTH_TOKEN: z.string().optional(),
  },
  client: {
    NEXT_PUBLIC_API_URL: z.string().url().default("http://localhost:8000"),
    NEXT_PUBLIC_SITE_URL: z.string().url().default("http://localhost:3000"),
    NEXT_PUBLIC_SENTRY_DSN: z.string().optional(),
    NEXT_PUBLIC_PLAUSIBLE_DOMAIN: z.string().optional(),
  },
  // Next.js' edge runtime substitutes process.env so it's not iterable —
  // we have to be explicit about which keys to pluck.
  runtimeEnv: {
    NODE_ENV: process.env.NODE_ENV,
    SENTRY_AUTH_TOKEN: process.env.SENTRY_AUTH_TOKEN,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
    NEXT_PUBLIC_SENTRY_DSN: process.env.NEXT_PUBLIC_SENTRY_DSN,
    NEXT_PUBLIC_PLAUSIBLE_DOMAIN: process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN,
  },
  // Skip validation during `next lint` / partial builds where the env
  // isn't fully populated yet.
  skipValidation: !!process.env.SKIP_ENV_VALIDATION,
  emptyStringAsUndefined: true,
});
