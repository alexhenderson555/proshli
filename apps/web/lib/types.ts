// Thin re-export layer. The authoritative type definitions now live in
// `@proshli/shared-types`, generated from the live OpenAPI document.
//
// We keep this stub so existing call sites (`@/lib/types`) keep working;
// new code should import directly from `@proshli/shared-types`.
//
// If you need a type that isn't re-exported yet, add it to
// `packages/shared-types/src/api.ts` (and run `pnpm -F @proshli/shared-types gen:offline`
// if the OpenAPI surface changed).

export type {
  EmployerActionLogOut,
  EmployerVacancyAnalyticsOut,
  EmployerVacancyPageOut,
  MatchScoreOut,
  MatchTier,
  RoleType,
  SeekerProfileOut,
  TokenResponse,
  UserOut,
  Vacancy,
} from "@proshli/shared-types";
