import preset from "@proshli/design-tokens/tailwind";

import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [preset],
} satisfies Config;
