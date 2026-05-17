import { expect, test } from "@playwright/test";

// next-themes persists the active theme in localStorage and toggles a
// class on <html> when the user picks light / dark / oled. With
// `defaultTheme="system"` and `enableSystem`, choosing "system" removes
// the explicit class entirely (next-themes lets prefers-color-scheme
// pick — under Playwright default this resolves to `light`).

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  // Wipe any previously stored theme so we start from the SSR default.
  await page.evaluate(() => window.localStorage.removeItem("theme"));
  // `clearCookies` would re-trigger locale detection, so we leave
  // cookies alone and instead navigate fresh.
  await page.reload();
});

test("theme switcher cycles through light / dark / oled / system", async ({ page }) => {
  const html = page.locator("html");
  const select = page.getByLabel("Переключить тему");

  // Light → class `light`.
  await select.selectOption("light");
  await expect(html).toHaveClass(/(^|\s)light(\s|$)/);

  // Dark → class `dark`.
  await select.selectOption("dark");
  await expect(html).toHaveClass(/(^|\s)dark(\s|$)/);

  // OLED → class `oled`.
  await select.selectOption("oled");
  await expect(html).toHaveClass(/(^|\s)oled(\s|$)/);

  // System → next-themes resolves to the OS preference; under Playwright
  // with no `colorScheme` option this is `light`, which means the
  // *resolved* theme class is `light` rather than `system`. We assert
  // we don't get a literal `system` class baked onto <html>.
  await select.selectOption("system");
  await expect(html).not.toHaveClass(/(^|\s)system(\s|$)/);
});
