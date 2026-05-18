import { defineConfig, devices } from "@playwright/test";

// CI runs ``next build`` before the Playwright step (see web-ci.yml),
// so we serve the production bundle here. That eliminates the cold-
// JIT lag of ``next dev`` — every first-hit route used to spend
// 15-30 s being compiled, which kept blowing past assertion timeouts
// for ``/en/vacancies``. Locally devs can still set
// ``PLAYWRIGHT_DEV=1`` to keep the dev server's HMR loop.
const useDevServer = process.env.PLAYWRIGHT_DEV === "1";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  retries: 0,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: useDevServer
      ? "npm run dev -- --port 3000"
      : "npm run start -- --port 3000",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 120000,
  },
});
