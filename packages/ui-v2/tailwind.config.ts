import preset from "@proshli/design-tokens/tailwind";
// eslint-disable-next-line @typescript-eslint/no-require-imports
import animate from "tailwindcss-animate";

import type { Config } from "tailwindcss";

// Dialog/Sheet/Tooltip полагаются на data-[state=open]:animate-in,
// slide-in-from-right и подобные классы — их даёт tailwindcss-animate.
// Без плагина анимации просто не отрабатывают (UI работает, но прыгает
// без перехода). Плагин подключаем здесь, а не в preset из design-tokens,
// потому что preset должен оставаться чисто декларативным (без runtime
// зависимостей) — каждый consumer добавляет plugins сам по необходимости.

export default {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [preset],
  plugins: [animate],
} satisfies Config;
