import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import tailwind from "@astrojs/tailwind";
import mdx from "@astrojs/mdx";

export default defineConfig({
  site: "https://proshli.ru",
  output: "static",
  i18n: {
    defaultLocale: "ru",
    locales: ["ru", "en"],
    routing: { prefixDefaultLocale: false },
  },
  integrations: [
    react(),
    tailwind({ applyBaseStyles: false }),
    mdx(),
    sitemap(),
  ],
  prefetch: { defaultStrategy: "viewport" },
});
