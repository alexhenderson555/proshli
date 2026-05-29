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
  ApplicationCountsOut,
  ApplicationOut,
  ApplicationStatus,
  EmployerActionLogOut,
  EmployerVacancyAnalyticsOut,
  EmployerVacancyPageOut,
  MatchScoreOut,
  MatchTier,
  PlanOut,
  RoleType,
  SeekerProfileOut,
  SubscriptionOut,
  TokenResponse,
  UserOut,
  Vacancy,
  VacancyStatsOut,
} from "@proshli/shared-types";

export interface CheckoutResponse {
  confirmation_url: string;
  payment_id: string;
  status: string;
}

export interface ResumeVersionOut {
  id: number;
  name: string;
  target_role: string;
  content: Record<string, unknown>;
  created_at: string;
}

export interface ResumeImproveRequest {
  target_role?: string;
  focus?: string;
}

export interface ResumeImproveResponse {
  summary: string;
  suggestions: string[];
  used_today: number;
  limit: number;
  backend: string;
}
