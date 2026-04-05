export type RoleType = "seeker" | "employer";

export type Vacancy = {
  id: number;
  source: string;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  experience_level: string;
  salary_from: number | null;
  salary_to: number | null;
  currency: string;
  description: string;
  published_at: string;
  applications_count: number;
  is_active: boolean;
  archived_at: string | null;
  is_deleted: boolean;
  deleted_at: string | null;
  is_promoted: boolean;
  promotion_expires_at: string | null;
  external_url?: string | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
};

export type UserOut = {
  id: number;
  email: string;
  role: RoleType;
  created_at: string;
};

export type SeekerProfileOut = {
  full_name: string;
  target_role: string;
  location: string;
  about: string;
  skills: string[];
  updated_at: string;
};

export type EmployerVacancyAnalyticsOut = {
  total: number;
  active: number;
  archived: number;
};

export type EmployerActionLogOut = {
  id: number;
  vacancy_id: number | null;
  action: string;
  meta: Record<string, unknown>;
  created_at: string;
};

export type EmployerVacancyPageOut = {
  items: Vacancy[];
  total: number;
  page: number;
  page_size: number;
};
