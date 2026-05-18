import { expect, test } from "@playwright/test";

// Match-score is gated on auth + a resume on file. Without either, the
// pill must not render — the anonymous visitor experience should look
// identical to pre-match-score. Authenticated flows that exercise the
// pill require seeded users + resumes; deferred to a future iteration
// when the e2e seed harness lands.

test.use({ locale: "ru-RU" });
test.setTimeout(60_000);

test("anonymous vacancy feed renders no match-pill", async ({ page, context }) => {
  await context.clearCookies();
  await page.goto("/vacancies");
  // The pill carries data-tier="strong|decent|stretch|longshot"; assert
  // there are zero such nodes for an unauthenticated session, even if
  // the feed itself renders cards.
  await expect(page.locator("[data-tier]")).toHaveCount(0, { timeout: 30_000 });
});

test.skip("authed seeker with resume sees match-pill", async () => {
  // Requires e2e auth + resume seed. The API-level test
  // `apps/api/tests/test_vacancies_include_match.py` exercises the same
  // path through the HTTP boundary.
});
