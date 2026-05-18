// Re-export of `cn` from the workspace UI package. We keep this stub so
// existing call sites (`@/lib/cn`) don't need to change all at once —
// new code should import directly from `@proshli/ui`.
//
// Wave 9 wired `transpilePackages: ["@proshli/ui", "@proshli/shared-types"]`
// in `next.config.ts` so the raw-`.ts(x)` workspace sources compile
// through the Next.js pipeline correctly.

export { cn } from "@proshli/ui";
