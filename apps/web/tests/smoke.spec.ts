import { expect, test } from "@playwright/test";

// Smoke tests assert against the RU strings on the default-locale URLs
// (`/auth`, `/vacancies`, ...). `as-needed` localePrefix means RU has
// no prefix, but the proxy still picks a locale per request — falling
// back to `Accept-Language` when no `OTKLIK_LOCALE` cookie is set.
// Playwright Chromium's default `Accept-Language` is `en-US`, so we
// pin the suite locale to `ru-RU` to keep cold sessions on RU.
test.use({ locale: "ru-RU" });

// `next dev` JIT-compiles each route on its first hit; on a cold CI
// runner this can blow past the default 5 s assertion timeout. We do
// not need fine-grained per-step latency assertions here, just that
// the page eventually paints, so widen the suite default.
test.setTimeout(60_000);
const ASSERT_TIMEOUT = { timeout: 30_000 } as const;

test.beforeEach(async ({ context }) => {
  // Clear any locale cookie a previous test may have set.
  await context.clearCookies();
});

test("auth page renders onboarding copy", async ({ page }) => {
  await page.goto("/auth");
  await expect(page.getByRole("heading", { name: "Onboarding Proshli" })).toBeVisible(ASSERT_TIMEOUT);
});

test("vacancies page renders search panel", async ({ page }) => {
  await page.goto("/vacancies");
  await expect(page.getByRole("heading", { name: "Лента вакансий" })).toBeVisible(ASSERT_TIMEOUT);
  await expect(page.getByRole("button", { name: "Найти вакансии" })).toBeVisible(ASSERT_TIMEOUT);
});

test("seeker and employer dashboards open", async ({ page }) => {
  await page.goto("/seeker");
  await expect(page.getByRole("heading", { name: "Профиль соискателя" })).toBeVisible(ASSERT_TIMEOUT);
  await page.goto("/employer");
  await expect(page.getByRole("heading", { name: "Кабинет работодателя" })).toBeVisible(ASSERT_TIMEOUT);
});
