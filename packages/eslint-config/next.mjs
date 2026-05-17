// Next.js + React layer on top of the base preset.

import base from "./index.mjs";

export default [
  ...base,
  {
    languageOptions: {
      globals: {
        // Browser globals — minimal set, just what App Router code reaches for.
        window: "readonly",
        document: "readonly",
        navigator: "readonly",
        fetch: "readonly",
        console: "readonly",
      },
    },
    rules: {
      // React 19 + Server Components: prefer Server Components by default.
      // We intentionally avoid the deprecated react-hooks/exhaustive-deps
      // rule here — react-compiler handles dependency tracking. Apps can
      // opt back in if they need to.
    },
  },
];
