import { expect, test } from "@playwright/test";

// `as-needed` strategy: RU is at `/`, EN is at `/en`.
//
// The locale cookie (`OTKLIK_LOCALE`) is sticky — if a previous test
// leaves it set to `en`, hitting `/` would redirect to `/en/...`. We
// clear cookies in `beforeEach` so each test starts from the default-
// locale state.
//
// Playwright Chromium's default `Accept-Language` is `en-US`, which
// would route a fresh cookie-less context to `/en` on first hit. Pin
// the suite locale to `ru-RU` so the cookie-less first request goes
// to RU as expected by the assertions below.
test.use({ locale: "ru-RU" });

test.beforeEach(async ({ context }) => {
  await context.clearCookies();
});

test("default locale renders RU strings on /", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/);
  // The hero copy contains a distinctive Russian phrase from messages/ru.json.
  await expect(page.getByText("пока AI ищет за вас")).toBeVisible();
  // `<html lang>` is set from `getLocale()` at SSR time.
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
});

test("/en renders English strings", async ({ page }) => {
  await page.goto("/en");
  // EN-only copy from messages/en.json.
  await expect(page.getByText("while AI searches for you")).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
});

test("locale switcher swaps language and preserves pathname", async ({ page }) => {
  await page.goto("/vacancies");
  // RU feed title is visible on the default locale.
  await expect(page.getByRole("heading", { name: "Лента вакансий" })).toBeVisible();

  // Flip locale to EN via the switcher.
  const switcher = page.getByLabel("Переключить язык");
  await switcher.selectOption("en");

  // Pathname preserved, EN copy now visible.
  await expect(page).toHaveURL(/\/en\/vacancies/);
  await expect(page.getByRole("heading", { name: "Vacancy feed" })).toBeVisible();
});
