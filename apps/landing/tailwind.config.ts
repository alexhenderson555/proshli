import type { Config } from "tailwindcss";
import preset from "@proshli/design-tokens/tailwind";

export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}"],
  presets: [preset],
  darkMode: "class",
} satisfies Config;
