import { expect, test } from "@playwright/test";

test("auth page renders onboarding copy", async ({ page }) => {
  await page.goto("/auth");
  await expect(page.getByRole("heading", { name: "Onboarding JobSkout" })).toBeVisible();
});

test("vacancies page renders search panel", async ({ page }) => {
  await page.goto("/vacancies");
  await expect(page.getByRole("heading", { name: "Лента вакансий" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Найти вакансии" })).toBeVisible();
});

test("seeker and employer dashboards open", async ({ page }) => {
  await page.goto("/seeker");
  await expect(page.getByRole("heading", { name: "Профиль соискателя" })).toBeVisible();
  await page.goto("/employer");
  await expect(page.getByRole("heading", { name: "Кабинет работодателя" })).toBeVisible();
});
