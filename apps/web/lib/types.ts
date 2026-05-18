// Thin re-export layer. The authoritative type definitions now live in
// `@otklik/shared-types`, generated from the live OpenAPI document.
//
// We keep this stub so existing call sites (`@/lib/types`) keep working;
// new code should import directly from `@otklik/shared-types`.
//
// If you need a type that isn't re-exported yet, add it to
// `packages/shared-types/src/api.ts` (and run `pnpm -F @otklik/shared-types gen:offline`
// if the OpenAPI surface changed).

export type {
  EmployerActionLogOut,
  EmployerVacancyAnalyticsOut,
  EmployerVacancyPageOut,
  RoleType,
  SeekerProfileOut,
  TokenResponse,
  UserOut,
  Vacancy,
} from "@otklik/shared-types";
