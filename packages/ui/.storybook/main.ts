import type { StorybookConfig } from "@storybook/react-vite";

// Storybook for `@proshli/ui`. Picks up `*.stories.tsx` next to each
// component so a story lives beside the source it documents. The vite
// final hook injects `@tailwindcss/vite` so utility classes resolve
// against the Proshli token set imported by `./preview.css`.

const config: StorybookConfig = {
  stories: ["../src/**/*.stories.@(ts|tsx)"],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  addons: [
    "@storybook/addon-essentials",
    "@storybook/addon-themes",
    "@storybook/addon-a11y",
  ],
  typescript: {
    reactDocgen: "react-docgen-typescript",
  },
  async viteFinal(viteConfig) {
    const { default: tailwindcss } = await import("@tailwindcss/vite");
    viteConfig.plugins = [...(viteConfig.plugins ?? []), tailwindcss()];
    return viteConfig;
  },
};

export default config;
