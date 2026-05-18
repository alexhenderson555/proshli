// Locale-aware navigation primitives.
//
// Use these (`Link`, `redirect`, `usePathname`, `useRouter`) anywhere we
// would have used `next/link` / `next/navigation` — they automatically
// prepend the active locale prefix when needed, so the rest of the app
// stays locale-agnostic.

import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
