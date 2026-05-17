import type {
  EmployerActionLogOut,
  EmployerVacancyAnalyticsOut,
  EmployerVacancyPageOut,
  SeekerProfileOut,
  TokenResponse,
  UserOut,
  Vacancy,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  token?: string | null;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  }
  const endpoint = `${API_BASE}${path}${query.size ? `?${query.toString()}` : ""}`;
  const headers: Record<string, string> = {};
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  // ``credentials: "include"`` so the ``otklik_access`` HttpOnly cookie
  // (set by the backend on register/login — F8) travels cross-origin from
  // localhost:3000 → localhost:8000 in dev and from the app domain → the
  // API domain in prod. The bearer ``Authorization`` header still wins
  // when ``options.token`` is supplied (transition state — we keep the
  // explicit-token call sites until the FE is fully cookie-only).
  const response = await fetch(endpoint, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    cache: "no-store",
    credentials: "include",
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) {
        detail = payload.detail;
      }
    } catch {
      // keep fallback
    }
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export const api = {
  register(email: string, password: string, role: "seeker" | "employer") {
    return request<TokenResponse>("/auth/register", {
      method: "POST",
      body: { email, password, role },
    });
  },
  login(email: string, password: string) {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
  },
  async logout(): Promise<void> {
    // Server-side cookie expiry (F8). The 204 response carries no JSON so
    // we short-circuit the JSON parse in ``request``.
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      credentials: "include",
      cache: "no-store",
    });
  },
  me(token: string) {
    return request<UserOut>("/users/me", { token });
  },
  vacancies(query: RequestOptions["query"]) {
    return request<Vacancy[]>("/vacancies", { query });
  },
  vacancy(id: number) {
    return request<Vacancy>(`/vacancies/${id}`);
  },
  seekerProfile(token: string) {
    return request<SeekerProfileOut>("/profiles/seeker", { token });
  },
  updateSeekerProfile(
    token: string,
    payload: {
      full_name: string;
      target_role: string;
      location: string;
      about: string;
      skills: string[];
    },
  ) {
    return request<SeekerProfileOut>("/profiles/seeker", {
      method: "PUT",
      token,
      body: payload,
    });
  },
  employerVacanciesPage(
    token: string,
    query: { status: string; sort_by: string; order: string; page: number; page_size: number },
  ) {
    return request<EmployerVacancyPageOut>("/vacancies/my/page", { token, query });
  },
  createEmployerVacancy(
    token: string,
    payload: {
      source: string;
      external_id: string;
      title: string;
      company: string;
      location: string;
      description: string;
      employment_type: string;
      experience_level: string;
      salary_from: number | null;
      salary_to: number | null;
      currency: string;
      applications_count: number;
    },
  ) {
    return request<Vacancy>("/vacancies", { method: "POST", token, body: payload });
  },
  updateVacancy(token: string, vacancyId: number, payload: Partial<Vacancy>) {
    return request<Vacancy>(`/vacancies/${vacancyId}`, {
      method: "PUT",
      token,
      body: payload,
    });
  },
  archiveVacancy(token: string, vacancyId: number) {
    return request<{ status: string }>(`/vacancies/${vacancyId}/archive`, {
      method: "POST",
      token,
    });
  },
  publishVacancy(token: string, vacancyId: number) {
    return request<{ status: string }>(`/vacancies/${vacancyId}/publish`, {
      method: "POST",
      token,
    });
  },
  promoteVacancy(token: string, vacancyId: number, days = 7) {
    return request<{ status: string }>(`/vacancies/${vacancyId}/promote`, {
      method: "POST",
      token,
      body: { days },
    });
  },
  deleteVacancy(token: string, vacancyId: number) {
    return request<{ status: string }>(`/vacancies/${vacancyId}`, {
      method: "DELETE",
      token,
    });
  },
  employerAnalytics(token: string) {
    return request<EmployerVacancyAnalyticsOut>("/vacancies/my/analytics", { token });
  },
  employerActions(token: string, query: { action?: string; limit?: number }) {
    return request<EmployerActionLogOut[]>("/vacancies/my/actions", {
      token,
      query,
    });
  },
  aiChat(token: string, message: string) {
    return request<{ accepted: boolean; message: string; extracted_filters?: Record<string, string> }>(
      "/ai/chat",
      {
        method: "POST",
        token,
        body: { message },
      },
    );
  },
};
