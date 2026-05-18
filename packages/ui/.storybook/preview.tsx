import "./preview.css";

import { withThemeByClassName } from "@storybook/addon-themes";
import type { Preview } from "@storybook/react";

// Each story is wrapped with a className toggle that flips the
// `<html>` class — same mechanism the production app uses. "Light" is
// the default (no class), "Dark" applies `.dark`, and "OLED" applies
// `.oled` for the true-black panel variant.

const preview: Preview = {
  parameters: {
    backgrounds: { disable: true },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
  },
  decorators: [
    withThemeByClassName({
      themes: {
        light: "",
        dark: "dark",
        oled: "oled",
      },
      defaultTheme: "light",
    }),
  ],
};

export default preview;
