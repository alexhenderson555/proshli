// Hand-written cross-cutting types + convenience re-exports of common
// schemas from the generated `./openapi` bundle.
//
// The OpenAPI codegen output stores every model under
// `components["schemas"]["XYZ"]` which is verbose at call sites. We
// expose a flat alias for each schema we use across the apps so callers
// can `import type { Vacancy, UserOut } from "@proshli/shared-types"` and
// stay backward-compatible with the pre-codegen world (Wave 9 follow-up).
//
// **Renames worth knowing about:**
//   - `VacancyOut`  →  `Vacancy`         (FE-friendlier name)
//   - `RoleType`    →  inlined from `UserOut.role` (the schema doesn't
//                       emit a top-level enum, so we extract it here).

import type { components } from "./openapi";

type Schemas = components["schemas"];

// ---------------------------------------------------------------------
// Hand-written types — kept even when codegen is offline.
// ---------------------------------------------------------------------

export interface ApiError {
  detail: string;
  request_id?: string;
}

export type SortOrder = "asc" | "desc";

// ---------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------

export type TokenResponse = Schemas["TokenResponse"];
export type LoginRequest = Schemas["LoginRequest"];
export type RegisterRequest = Schemas["RegisterRequest"];

// ---------------------------------------------------------------------
// Users / profiles
// ---------------------------------------------------------------------

export type UserOut = Schemas["UserOut"];
export type RoleType = UserOut["role"];
export type SeekerProfileOut = Schemas["SeekerProfileOut"];
export type SeekerProfileUpdate = Schemas["SeekerProfileUpdate"];
export type EmployerProfileOut = Schemas["EmployerProfileOut"];
export type EmployerProfileUpdate = Schemas["EmployerProfileUpdate"];

// ---------------------------------------------------------------------
// Vacancies
// ---------------------------------------------------------------------

export type MatchTier = "strong" | "decent" | "stretch" | "longshot";
export interface MatchScoreOut {
  score: number;
  tier: MatchTier;
}

// VacancyOut from the backend now also carries the match-score fields
// (added 2026-05-18). The OpenAPI bundle hasn't been regenerated yet —
// when it is, this intersection becomes redundant and can be deleted.
export type Vacancy = Schemas["VacancyOut"] & {
  match_score?: number | null;
  match_tier?: MatchTier | null;
};
export type VacancyCreateRequest = Schemas["VacancyCreateRequest"];
export type VacancyUpdateRequest = Schemas["VacancyUpdateRequest"];
export type VacancyPromoteRequest = Schemas["VacancyPromoteRequest"];
export type EmployerVacancyPageOut = Schemas["EmployerVacancyPageOut"];
export type EmployerVacancyAnalyticsOut = Schemas["EmployerVacancyAnalyticsOut"];
export type EmployerActionLogOut = Schemas["EmployerActionLogOut"];

// ---------------------------------------------------------------------
// Billing
// ---------------------------------------------------------------------

export type CheckoutRequest = Schemas["CheckoutRequest"];
export type CheckoutResponse = Schemas["CheckoutResponse"];
export type PlanOut = Schemas["PlanOut"];
export type SubscriptionOut = Schemas["SubscriptionOut"];

// ---------------------------------------------------------------------
// AI
// ---------------------------------------------------------------------

export type AiChatRequest = Schemas["AiChatRequest"];
export type AiChatResponse = Schemas["AiChatResponse"];

// ---------------------------------------------------------------------
// Digest / Telegram link flow
// ---------------------------------------------------------------------

export type DigestPreferenceOut = Schemas["DigestPreferenceOut"];
export type DigestPreferenceUpdate = Schemas["DigestPreferenceUpdate"];
export type DigestItem = Schemas["DigestItem"];
export type DigestPreviewOut = Schemas["DigestPreviewOut"];
export type TelegramLinkCodeOut = Schemas["TelegramLinkCodeOut"];
export type TelegramLinkConsumeRequest = Schemas["TelegramLinkConsumeRequest"];
export type TelegramBotLoginRequest = Schemas["TelegramBotLoginRequest"];

// ---------------------------------------------------------------------
// Resumes
// ---------------------------------------------------------------------

export type ResumeOut = Schemas["ResumeOut"];
export type ResumeVersionOut = Schemas["ResumeVersionOut"];
export type ResumeVersionCreate = Schemas["ResumeVersionCreate"];
