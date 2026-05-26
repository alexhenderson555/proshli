# Phase 1: Astro Landing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Поднять Vercel/Geist-style лендинг `proshli.ru` на Astro 5 с AI-демо hero, particle backdrop, pricing/employers/about/FAQ, блогом и self-deployed контейнером. По окончании этой фазы `proshli.ru` обновлён, `app.proshli.ru` остаётся текущим Next.js (рерайт — Phase 2).

**Architecture:** Новое приложение `apps/landing/` на Astro 5 (Server Islands + View Transitions). React-islands только там где нужна интерактивность (hero AI-demo, animations, scroll-triggers). Tailwind v4 с preset из `@proshli/design-tokens`. Демо-AI hero — статически захардкоженный поток (не вызывает прод-API), чтобы лендинг не зависел от uptime API и не съедал AI-бюджет анонимов.

**Tech Stack:** Astro 5, @astrojs/react, @astrojs/tailwind, Tailwind v4, Framer Motion, Spline (или r3f) для 3D hero, MDX для блога, `@astrojs/sitemap`, `@astrojs/i18n`.

**Working directory:** `C:/Users/Alex/Cursor/jobskout/`

**Prerequisite:** Phase 0 завершена (см. `docs/superpowers/plans/2026-05-26-phase-0-foundation.md`) — `packages/design-tokens` и `packages/ui-v2` готовы и линтятся.

**Reference spec:** `docs/superpowers/specs/2026-05-26-frontend-million-design.md`

---

## ⚠️ КРИТИЧНО: Anti-Slop правила

**Перед началом любой задачи прочитай секцию «Voice & Anti-Slop Rules» в спеке.** Это не «nice to have» — это критерий приёмки. Каждая страница проходит 5-пунктовую проверку перед merge (см. спеку, конец секции).

Конкретные адаптации кода в этом плане:

- **Task 3 (Hero):** в плане предложен центрированный hero с большим заголовком + CTA — это AI-pattern. Адаптировать: сдвинуть hero влево или сделать асимметричным (input справа, заголовок слева, или vice versa). Уменьшить размер заголовка, добавить short opener-параграф от первого лица.
- **Task 4 (How It Works):** в плане 3 одинаковые карточки с emoji-иконками (📄🎯📬). **Не использовать emoji.** Заменить на: одна большая иллюстрация процесса слева + 3 коротких описания справа (asymmetric layout), либо custom SVG-иконки (не из Heroicons), либо просто пронумерованные параграфы без иконок.
- **Task 5 (FAQ):** copy уже сейчас приемлемый, но проверь чтобы не было «We believe» / «Our mission».
- **Task 6 (About):** copy в плане OK (от первого лица, упомянуты технические детали). Сохранить этот тон.
- **Task 7 (Blog):** 3 затравочных поста в плане написаны OK-тоном (specific, technical), но проверь и усиль — реальные числа, конкретные грабли, ругательство «задолбался» допустимо.

Запрещённые слова в любом коде/копирайте (RU+EN):
`discover, seamless, effortless, powered by AI, unleash, harness, revolutionary, cutting-edge, state-of-the-art, elevate, We believe, Our mission, Trusted by thousands` (если нет реального списка кастомеров).

Acceptance check для каждой созданной страницы (запускать сам перед commit):

1. **3-second test** — посмотри на скриншот, если выглядит как «нагенерил Lovable/V0» — переделать.
2. **`grep -i "discover\|seamless\|effortless\|powered by ai\|unleash"`** в HTML → 0 матчей.
3. **Emoji в feature-секциях** — 0. (В footer/personal — можно.)
4. **Hero не должен быть text-center + button-center.** Хоть какая-то асимметрия обязательна.
5. **3 одинаковые секции подряд = провал.** Структура страниц должна варьироваться.

---

## File Structure

```
apps/landing/
├── package.json
├── astro.config.mjs
├── tailwind.config.ts            ← extends preset из @proshli/design-tokens
├── tsconfig.json
├── .gitignore
├── Dockerfile
├── public/
│   ├── favicon.svg
│   ├── og/default.png            ← статичная default OG-картинка
│   └── fonts/                    ← Inter Variable + JetBrains Mono Variable self-hosted
├── src/
│   ├── env.d.ts
│   ├── pages/
│   │   ├── index.astro           ← homepage
│   │   ├── pricing.astro
│   │   ├── employers.astro
│   │   ├── about.astro
│   │   ├── blog/
│   │   │   ├── index.astro
│   │   │   └── [...slug].astro
│   │   ├── legal/
│   │   │   ├── privacy.astro
│   │   │   ├── terms.astro
│   │   │   └── oferta.astro
│   │   └── en/                   ← English mirror (Astro i18n)
│   │       └── ...
│   ├── layouts/
│   │   ├── BaseLayout.astro      ← <html>, <head>, fonts, theme
│   │   └── BlogLayout.astro
│   ├── components/
│   │   ├── Header.astro
│   │   ├── Footer.astro
│   │   ├── HeroAiDemo.tsx        ← React island
│   │   ├── HeroBackdrop.tsx      ← React island (Spline | particles)
│   │   ├── FeatureCard.astro
│   │   ├── PricingCard.astro
│   │   ├── GradientText.astro
│   │   └── KbdShortcut.astro
│   ├── content/                  ← Astro Content Collections
│   │   ├── config.ts
│   │   └── blog/
│   │       ├── ai-vs-handcraft.md
│   │       ├── how-it-works.md
│   │       └── digest-vs-search.md
│   └── lib/
│       ├── demo-stream.ts        ← симуляция SSE для hero demo
│       └── analytics.ts          ← Plausible loader
└── ...
deploy/
├── docker-compose.prod.yml       ← добавляем proshli-landing service
└── Caddyfile                     ← переключаем proshli.ru на proshli-landing
.github/workflows/
└── build-and-push.yml            ← добавляем landing в matrix
```

---

## Task 1: Init `apps/landing/` с Astro 5

**Files:**
- Create: `apps/landing/package.json`
- Create: `apps/landing/astro.config.mjs`
- Create: `apps/landing/tsconfig.json`
- Create: `apps/landing/tailwind.config.ts`
- Create: `apps/landing/.gitignore`
- Create: `apps/landing/src/env.d.ts`

- [ ] **Step 1: Создать пакет**

`apps/landing/package.json`:

```json
{
  "name": "@proshli/landing",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "astro dev --port 4321",
    "build": "astro build",
    "preview": "astro preview --port 4321",
    "lint": "eslint src",
    "type-check": "astro check"
  },
  "dependencies": {
    "@astrojs/check": "^0.9.0",
    "@astrojs/mdx": "^4.0.0",
    "@astrojs/react": "^4.0.0",
    "@astrojs/sitemap": "^3.2.0",
    "@astrojs/tailwind": "^5.1.0",
    "@proshli/design-tokens": "workspace:*",
    "@proshli/ui-v2": "workspace:*",
    "astro": "^5.0.0",
    "framer-motion": "^11.11.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "tailwindcss": "^3.4.0"
  },
  "devDependencies": {
    "@proshli/tsconfig": "workspace:*",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.6.0"
  }
}
```

Примечание: Tailwind v4 ещё не имеет стабильного Astro-интегратора на момент написания. Если на момент исполнения v4 уже зрелая — мигрировать через PR в Task 4. Иначе оставляем v3 (что соответствует текущему `apps/web/`).

`apps/landing/astro.config.mjs`:

```javascript
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
```

`apps/landing/tailwind.config.ts`:

```typescript
import type { Config } from "tailwindcss";
import preset from "@proshli/design-tokens/tailwind";

export default {
  content: ["./src/**/*.{astro,html,js,jsx,md,mdx,ts,tsx}"],
  presets: [preset],
  darkMode: "class",
} satisfies Config;
```

`apps/landing/tsconfig.json`:

```json
{
  "extends": "astro/tsconfigs/strict",
  "include": ["src/**/*", "astro.config.mjs"],
  "exclude": ["dist", "node_modules"]
}
```

`apps/landing/.gitignore`:

```
dist/
node_modules/
.astro/
*.tsbuildinfo
```

- [ ] **Step 2: Установить deps и проверить dev**

```bash
cd apps/landing && pnpm install
pnpm dev
```

Expected: Astro стартует на `localhost:4321`, открывается белая страница (404 пока нет pages).

Открыть `http://localhost:4321/` — должно вернуться 404 (это правильно).

- [ ] **Step 3: Создать BaseLayout**

`apps/landing/src/layouts/BaseLayout.astro`:

```astro
---
import "@proshli/design-tokens/tokens.css";
import "../styles/global.css";

interface Props {
  title: string;
  description?: string;
  ogImage?: string;
  noindex?: boolean;
}

const {
  title,
  description = "Premium IT job search powered by AI. Discover roles that match your resume, not just keywords.",
  ogImage = "/og/default.png",
  noindex = false,
} = Astro.props;

const canonical = new URL(Astro.url.pathname, Astro.site);
---

<!doctype html>
<html lang={Astro.currentLocale || "ru"} class="dark">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="generator" content={Astro.generator} />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="canonical" href={canonical} />
    {noindex && <meta name="robots" content="noindex" />}

    <title>{title}</title>
    <meta name="description" content={description} />

    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:image" content={new URL(ogImage, Astro.site)} />
    <meta property="og:url" content={canonical} />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />

    <link rel="preconnect" href="https://api.proshli.ru" crossorigin />
  </head>
  <body class="min-h-screen bg-landing-bg-primary text-landing-text-primary font-sans antialiased">
    <slot />
  </body>
</html>
```

`apps/landing/src/styles/global.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    color-scheme: dark;
  }
  body {
    font-feature-settings: "cv11", "ss01", "ss03";
  }
}
```

- [ ] **Step 4: Создать заглушку homepage**

`apps/landing/src/pages/index.astro`:

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
---

<BaseLayout title="Proshli — AI читает вакансии, ты не читаешь">
  <main class="flex min-h-screen items-center justify-center">
    <h1 class="text-72 font-bold tracking-tight">Proshli</h1>
  </main>
</BaseLayout>
```

`http://localhost:4321/` теперь возвращает большой "Proshli" по центру тёмного экрана.

- [ ] **Step 5: Commit**

```bash
git add apps/landing
git commit -m "feat(landing): scaffold Astro 5 + Tailwind + base layout"
```

---

## Task 2: Header + Footer

**Files:**
- Create: `apps/landing/src/components/Header.astro`
- Create: `apps/landing/src/components/Footer.astro`
- Modify: `apps/landing/src/layouts/BaseLayout.astro` (use them)

- [ ] **Step 1: Header**

`apps/landing/src/components/Header.astro`:

```astro
---
const links = [
  { href: "/pricing", label: "Pricing" },
  { href: "/employers", label: "Для работодателей" },
  { href: "/blog", label: "Блог" },
  { href: "/about", label: "О нас" },
];
const currentLocale = Astro.currentLocale || "ru";
---

<header class="fixed top-0 left-0 right-0 z-40 border-b border-white/5 bg-landing-bg-primary/70 backdrop-blur-xl">
  <div class="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
    <a href="/" class="flex items-center gap-2 font-bold tracking-tight">
      <span class="text-18">Proshli</span>
    </a>
    <nav class="hidden items-center gap-6 md:flex">
      {links.map((l) => (
        <a href={l.href} class="text-13 text-landing-text-muted hover:text-landing-text-primary transition-colors">
          {l.label}
        </a>
      ))}
    </nav>
    <div class="flex items-center gap-3">
      <a href={currentLocale === "ru" ? "/en/" : "/"} class="text-12 text-landing-text-muted hover:text-landing-text-primary">
        {currentLocale === "ru" ? "EN" : "RU"}
      </a>
      <a href="https://app.proshli.ru/auth/login" class="text-13 text-landing-text-muted hover:text-landing-text-primary">Войти</a>
      <a
        href="https://app.proshli.ru/auth/register"
        class="rounded-md bg-gradient-to-r from-landing-accent-start to-landing-accent-end px-3 h-8 inline-flex items-center text-13 font-medium text-white shadow-glow"
      >
        Регистрация
      </a>
    </div>
  </div>
</header>
```

- [ ] **Step 2: Footer**

`apps/landing/src/components/Footer.astro`:

```astro
<footer class="border-t border-white/5 mt-32 py-12">
  <div class="mx-auto max-w-6xl px-6 grid grid-cols-2 md:grid-cols-4 gap-8 text-13">
    <div>
      <div class="font-semibold mb-3">Proshli</div>
      <p class="text-landing-text-muted">AI читает вакансии, ты не читаешь.</p>
    </div>
    <div>
      <div class="font-semibold mb-3">Продукт</div>
      <ul class="space-y-2 text-landing-text-muted">
        <li><a href="/pricing" class="hover:text-landing-text-primary">Тарифы</a></li>
        <li><a href="/employers" class="hover:text-landing-text-primary">Работодателям</a></li>
      </ul>
    </div>
    <div>
      <div class="font-semibold mb-3">Компания</div>
      <ul class="space-y-2 text-landing-text-muted">
        <li><a href="/about" class="hover:text-landing-text-primary">О нас</a></li>
        <li><a href="/blog" class="hover:text-landing-text-primary">Блог</a></li>
      </ul>
    </div>
    <div>
      <div class="font-semibold mb-3">Правовое</div>
      <ul class="space-y-2 text-landing-text-muted">
        <li><a href="/legal/privacy" class="hover:text-landing-text-primary">Privacy</a></li>
        <li><a href="/legal/terms" class="hover:text-landing-text-primary">Terms</a></li>
        <li><a href="/legal/oferta" class="hover:text-landing-text-primary">Оферта</a></li>
      </ul>
    </div>
  </div>
  <div class="mx-auto max-w-6xl px-6 mt-12 pt-6 border-t border-white/5 text-12 text-landing-text-muted">
    © 2026 Proshli. Сделано в России 🇷🇺.
  </div>
</footer>
```

- [ ] **Step 3: Подключить в BaseLayout**

Заменить `<body>` content в `BaseLayout.astro`:

```astro
---
import Header from "../components/Header.astro";
import Footer from "../components/Footer.astro";
// ... existing imports + props ...
---

<!doctype html>
<html ...>
  <head>...</head>
  <body class="min-h-screen bg-landing-bg-primary text-landing-text-primary font-sans antialiased">
    <Header />
    <main class="pt-14"><slot /></main>
    <Footer />
  </body>
</html>
```

- [ ] **Step 4: Commit**

```bash
git add apps/landing/src/components/Header.astro apps/landing/src/components/Footer.astro apps/landing/src/layouts/BaseLayout.astro
git commit -m "feat(landing): add Header + Footer with i18n locale toggle"
```

---

## Task 3: Hero с AI-демо (главная wow-фича)

Hero — React island, симулирует SSE-стрим карточек вакансий после ввода запроса. **Не вызывает реальный API** — данные захардкожены, симуляция через `setTimeout`. Это даёт wow без зависимости от uptime backend и без AI-бюджета.

**Files:**
- Create: `apps/landing/src/components/HeroAiDemo.tsx`
- Create: `apps/landing/src/components/HeroBackdrop.tsx`
- Create: `apps/landing/src/lib/demo-stream.ts`
- Modify: `apps/landing/src/pages/index.astro`

- [ ] **Step 1: demo-stream симулятор**

`apps/landing/src/lib/demo-stream.ts`:

```typescript
export interface DemoCard {
  company: string;
  title: string;
  match: number;
  tags: string[];
  salary: string;
  location: string;
}

const DEMO_QUERIES: Record<string, DemoCard[]> = {
  default: [
    { company: "Yandex · Platform", title: "Senior Backend Engineer", match: 94, tags: ["Go", "Kafka"], salary: "₽550K", location: "Remote" },
    { company: "Tinkoff · CoreBank", title: "Backend Lead", match: 89, tags: ["Go", "Postgres"], salary: "₽600K", location: "Hybrid" },
    { company: "Avito · Search", title: "Search Engineer", match: 86, tags: ["Python", "Elastic"], salary: "₽480K", location: "Office" },
  ],
};

export async function* simulateStream(_query: string): AsyncGenerator<
  { type: "text"; value: string } | { type: "card"; value: DemoCard }
> {
  // Лёгкий typing-эффект для текста-ответа.
  const intro = "Нашёл 3 вакансии по твоему запросу:";
  for (const chunk of intro.match(/.{1,4}/g) ?? []) {
    yield { type: "text", value: chunk };
    await sleep(40);
  }
  await sleep(200);
  for (const card of DEMO_QUERIES.default) {
    yield { type: "card", value: card };
    await sleep(280);
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
```

- [ ] **Step 2: HeroAiDemo React island**

`apps/landing/src/components/HeroAiDemo.tsx`:

```tsx
import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { type DemoCard, simulateStream } from "../lib/demo-stream";

export default function HeroAiDemo() {
  const [query, setQuery] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [answer, setAnswer] = useState("");
  const [cards, setCards] = useState<DemoCard[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || streaming) return;
    setStreaming(true);
    setAnswer("");
    setCards([]);
    for await (const frame of simulateStream(query)) {
      if (frame.type === "text") setAnswer((prev) => prev + frame.value);
      else setCards((prev) => [...prev, frame.value]);
    }
    setStreaming(false);
  };

  return (
    <div className="w-full max-w-2xl">
      <form onSubmit={handleSubmit} className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='"Backend в Москву от 400К"'
          disabled={streaming}
          className="w-full h-14 px-5 pr-32 rounded-xl bg-white/5 border border-white/10 text-16 text-white placeholder:text-white/40 focus:outline-none focus:border-landing-accent-start focus:shadow-glow transition-all"
        />
        <button
          type="submit"
          disabled={streaming || !query.trim()}
          className="absolute right-2 top-2 h-10 px-4 rounded-lg bg-gradient-to-r from-landing-accent-start to-landing-accent-end text-13 font-medium text-white shadow-glow disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {streaming ? "AI думает..." : "Спросить"}
        </button>
      </form>

      <AnimatePresence>
        {answer && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-6 text-14 text-white/80">
            {answer}
            {streaming && <span className="inline-block w-2 h-4 ml-1 bg-landing-accent-start animate-pulse" />}
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-4 space-y-3">
        <AnimatePresence>
          {cards.map((card, i) => (
            <motion.div
              key={`${card.company}-${i}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm hover:border-landing-accent-start/40 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-14 font-semibold text-white">{card.title}</div>
                  <div className="text-13 text-white/60 mt-0.5">
                    {card.company} · {card.location} · {card.salary}
                  </div>
                </div>
                <div className="text-13 font-medium text-landing-accent-start">{card.match}%</div>
              </div>
              <div className="flex gap-1.5 mt-3 flex-wrap">
                {card.tags.map((t) => (
                  <span key={t} className="text-11 px-2 py-0.5 rounded-full border border-white/10 text-white/70">
                    {t}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {cards.length === 3 && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="mt-6 text-center">
          <a
            href="https://app.proshli.ru/auth/register"
            className="inline-flex items-center gap-2 text-14 px-5 h-10 rounded-lg bg-gradient-to-r from-landing-accent-start to-landing-accent-end text-white font-medium shadow-glow"
          >
            Зарегистрируйся, чтобы получать дайджест →
          </a>
        </motion.div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: HeroBackdrop (тонкая 3D-подложка)**

Для прототипа — без Spline (избегаем 200KB+). Простая SVG-particle сетка с CSS-анимацией.

`apps/landing/src/components/HeroBackdrop.tsx`:

```tsx
export default function HeroBackdrop() {
  // Чисто декоративный backdrop. Слой -1, не блокирует клики.
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_30%,rgba(124,58,237,0.18)_0%,transparent_60%)]" />
      <div className="absolute inset-0 opacity-30">
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.04)" stroke-width="1" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>
    </div>
  );
}
```

Phase 1.5 — если по итогам Lighthouse-audit будет нужно больше wow, заменить на Spline сцену или r3f-particles (см. Risks ниже).

- [ ] **Step 4: Собрать homepage**

Полностью заменить `apps/landing/src/pages/index.astro`:

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
import HeroAiDemo from "../components/HeroAiDemo.tsx";
import HeroBackdrop from "../components/HeroBackdrop.tsx";
---

<BaseLayout title="Proshli — AI читает вакансии, ты не читаешь" description="Premium AI-powered job search для IT. Опиши что ищешь — AI найдёт матчи, читать ничего не надо.">
  <section class="relative min-h-[calc(100vh-3.5rem)] flex flex-col items-center justify-center px-6 overflow-hidden">
    <HeroBackdrop client:load />
    <h1 class="text-48 md:text-72 font-extrabold tracking-tight text-center leading-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-purple-300">
      AI читает вакансии,<br />ты не читаешь
    </h1>
    <p class="mt-6 text-18 text-landing-text-muted text-center max-w-xl">
      Опиши что ищешь словами. AI находит матчи по резюме и шлёт дайджест в Telegram.
    </p>
    <div class="mt-12 w-full flex justify-center">
      <HeroAiDemo client:load />
    </div>
  </section>

  <!-- Заглушки секций — наполняем в Tasks 4-7 -->
  <section class="py-24 px-6"><div class="mx-auto max-w-6xl"><h2 class="text-32 font-bold">Как работает</h2></div></section>
  <section class="py-24 px-6"><div class="mx-auto max-w-6xl"><h2 class="text-32 font-bold">Тарифы</h2></div></section>
  <section class="py-24 px-6"><div class="mx-auto max-w-6xl"><h2 class="text-32 font-bold">FAQ</h2></div></section>
</BaseLayout>
```

- [ ] **Step 5: Запустить dev и проверить**

```bash
cd apps/landing && pnpm dev
```

Открыть `http://localhost:4321/`. Должно быть:
- Тёмный фон с фиолетовым radial-glow
- Большой заголовок "AI читает вакансии, ты не читаешь" с gradient-текстом
- Input под ним
- Нажми Enter с любым текстом → 3 карточки появляются по очереди с анимацией
- После 3-й карточки — CTA «Зарегистрируйся»

Если что-то сломано — проверить imports, проверить что Tailwind генерит классы (color-tokens пробрасываются через preset из `@proshli/design-tokens`).

- [ ] **Step 6: Commit**

```bash
git add apps/landing
git commit -m "feat(landing): hero AI demo with simulated stream + animated cards"
```

---

## Task 4: How It Works + Pricing секции на homepage

**Files:**
- Modify: `apps/landing/src/pages/index.astro`
- Create: `apps/landing/src/components/FeatureCard.astro`
- Create: `apps/landing/src/components/PricingCard.astro`

- [ ] **Step 1: FeatureCard**

`apps/landing/src/components/FeatureCard.astro`:

```astro
---
interface Props { title: string; description: string; icon?: string; }
const { title, description, icon } = Astro.props;
---

<div class="rounded-2xl border border-white/10 bg-white/[0.02] p-6 hover:border-landing-accent-start/40 transition-colors">
  {icon && <div class="text-32 mb-4">{icon}</div>}
  <h3 class="text-18 font-semibold mb-2">{title}</h3>
  <p class="text-14 text-landing-text-muted leading-loose">{description}</p>
</div>
```

- [ ] **Step 2: PricingCard**

`apps/landing/src/components/PricingCard.astro`:

```astro
---
interface Props {
  name: string;
  price: string;
  period: string;
  features: string[];
  cta: string;
  ctaHref: string;
  featured?: boolean;
}
const { name, price, period, features, cta, ctaHref, featured = false } = Astro.props;
---

<div class:list={[
  "rounded-2xl p-8 flex flex-col",
  featured
    ? "bg-gradient-to-br from-landing-accent-start/20 to-landing-accent-end/10 border-2 border-landing-accent-start shadow-glow"
    : "bg-white/[0.02] border border-white/10",
]}>
  {featured && <div class="text-11 uppercase tracking-wide font-bold text-landing-accent-start mb-3">Популярный</div>}
  <h3 class="text-24 font-bold mb-2">{name}</h3>
  <div class="flex items-baseline gap-1 mb-6">
    <span class="text-32 font-bold">{price}</span>
    <span class="text-13 text-landing-text-muted">/ {period}</span>
  </div>
  <ul class="space-y-3 text-14 mb-8 flex-grow">
    {features.map((f) => (
      <li class="flex gap-2 text-landing-text-muted">
        <span class="text-landing-accent-start">✓</span>
        <span>{f}</span>
      </li>
    ))}
  </ul>
  <a
    href={ctaHref}
    class:list={[
      "block text-center rounded-lg h-11 leading-[2.75rem] text-14 font-medium transition-opacity",
      featured
        ? "bg-gradient-to-r from-landing-accent-start to-landing-accent-end text-white"
        : "border border-white/20 text-white hover:bg-white/5",
    ]}
  >
    {cta}
  </a>
</div>
```

- [ ] **Step 3: Заменить заглушки в index.astro**

Заменить три `<section>` заглушки на конкретный контент. Полный обновлённый файл:

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
import HeroAiDemo from "../components/HeroAiDemo.tsx";
import HeroBackdrop from "../components/HeroBackdrop.tsx";
import FeatureCard from "../components/FeatureCard.astro";
import PricingCard from "../components/PricingCard.astro";

const howItWorks = [
  { icon: "📄", title: "Загрузи резюме", description: "PDF или текст. AI извлекает скиллы, опыт и желаемый стек за 5 секунд." },
  { icon: "🎯", title: "Получи матчи", description: "AI читает вакансии, ранжирует по match-score и отдаёт топ-10. Без ручного перебора." },
  { icon: "📬", title: "Дайджест в Telegram", description: "Каждое утро новые матчи в чате. Без push-спама, без писем в почту." },
];

const tiers = [
  {
    name: "Free",
    price: "₽0",
    period: "навсегда",
    features: ["3 матч-запроса в день", "Дайджест раз в неделю", "Базовый AI-поиск"],
    cta: "Начать",
    ctaHref: "https://app.proshli.ru/auth/register",
  },
  {
    name: "Pro",
    price: "₽490",
    period: "месяц",
    features: ["Безлимит AI-запросов", "Дайджест каждый день", "Match-score с обоснованием", "AI-улучшение резюме"],
    cta: "Попробовать Pro",
    ctaHref: "https://app.proshli.ru/billing?plan=pro",
    featured: true,
  },
  {
    name: "Employer",
    price: "₽4 900",
    period: "месяц",
    features: ["Размещение вакансий", "Кандидаты с скриннингом", "Команда до 5 человек", "Приоритетная поддержка"],
    cta: "Для компаний",
    ctaHref: "https://app.proshli.ru/employer",
  },
];
---

<BaseLayout title="Proshli — AI читает вакансии, ты не читаешь">
  <!-- Hero -->
  <section class="relative min-h-[calc(100vh-3.5rem)] flex flex-col items-center justify-center px-6 overflow-hidden">
    <HeroBackdrop client:load />
    <h1 class="text-48 md:text-72 font-extrabold tracking-tight text-center leading-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-purple-300">
      AI читает вакансии,<br />ты не читаешь
    </h1>
    <p class="mt-6 text-18 text-landing-text-muted text-center max-w-xl">
      Опиши что ищешь словами. AI находит матчи по резюме и шлёт дайджест в Telegram.
    </p>
    <div class="mt-12 w-full flex justify-center">
      <HeroAiDemo client:load />
    </div>
  </section>

  <!-- How it works -->
  <section class="py-32 px-6">
    <div class="mx-auto max-w-6xl">
      <h2 class="text-32 md:text-48 font-bold tracking-tight text-center mb-4">Как работает</h2>
      <p class="text-16 text-landing-text-muted text-center mb-16 max-w-xl mx-auto">Три шага от резюме до первого матча. Без ручного перебора.</p>
      <div class="grid md:grid-cols-3 gap-6">
        {howItWorks.map((f) => <FeatureCard {...f} />)}
      </div>
    </div>
  </section>

  <!-- Pricing -->
  <section class="py-32 px-6 border-t border-white/5">
    <div class="mx-auto max-w-6xl">
      <h2 class="text-32 md:text-48 font-bold tracking-tight text-center mb-4">Тарифы</h2>
      <p class="text-16 text-landing-text-muted text-center mb-16 max-w-xl mx-auto">Без скрытых платежей, без минимального срока.</p>
      <div class="grid md:grid-cols-3 gap-6">
        {tiers.map((t) => <PricingCard {...t} />)}
      </div>
    </div>
  </section>

  <!-- FAQ заглушка — Task 5 -->
  <section class="py-32 px-6 border-t border-white/5">
    <div class="mx-auto max-w-3xl">
      <h2 class="text-32 md:text-48 font-bold tracking-tight text-center mb-16">FAQ</h2>
      <!-- наполнение в Task 5 -->
    </div>
  </section>
</BaseLayout>
```

- [ ] **Step 4: Проверить визуально**

`pnpm dev` → `localhost:4321`. Должны быть: Hero, How It Works (3 карточки), Pricing (3 карточки, средняя выделена), FAQ-заглушка.

- [ ] **Step 5: Commit**

```bash
git add apps/landing
git commit -m "feat(landing): how-it-works + pricing sections on homepage"
```

---

## Task 5: FAQ-секция

**Files:**
- Modify: `apps/landing/src/pages/index.astro` (наполнить FAQ-секцию)
- Create: `apps/landing/src/components/FaqItem.astro`

- [ ] **Step 1: FaqItem с native `<details>` (без JS)**

`apps/landing/src/components/FaqItem.astro`:

```astro
---
interface Props { question: string }
const { question } = Astro.props;
---

<details class="group rounded-xl border border-white/10 bg-white/[0.02] open:border-landing-accent-start/40 transition-colors">
  <summary class="flex items-center justify-between cursor-pointer list-none p-5 text-14 font-medium">
    <span>{question}</span>
    <svg class="w-4 h-4 text-landing-text-muted transition-transform group-open:rotate-180" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M6 9l6 6 6-6" />
    </svg>
  </summary>
  <div class="px-5 pb-5 text-13 text-landing-text-muted leading-loose">
    <slot />
  </div>
</details>
```

- [ ] **Step 2: Наполнить FAQ-секцию**

В `apps/landing/src/pages/index.astro`, заменить FAQ-заглушку на:

```astro
<section class="py-32 px-6 border-t border-white/5">
  <div class="mx-auto max-w-3xl">
    <h2 class="text-32 md:text-48 font-bold tracking-tight text-center mb-16">FAQ</h2>
    <div class="space-y-3">
      <FaqItem question="Какие источники вакансий вы используете?">
        Подключены HeadHunter, Habr Career, тематические Telegram-каналы (~50 проверенных IT-каналов).
        Парсинг происходит каждый час, дедупликация по нормализованным заголовкам.
      </FaqItem>
      <FaqItem question="AI правда читает мои данные?">
        Резюме обрабатывается embedding-моделью на нашей стороне для семантического поиска. Текст не отправляется
        третьим сторонам кроме провайдера LLM (Anthropic) при запросах к AI-ассистенту. Можно удалить аккаунт
        одной кнопкой в настройках.
      </FaqItem>
      <FaqItem question="Чем отличаетесь от hh.ru?">
        Мы не пытаемся заменить hh — мы аккумулируем вакансии из десятков источников и ранжируем по совпадению
        с твоим резюме. Ты не листаешь — AI делает это за тебя и присылает топ-10 в Telegram.
      </FaqItem>
      <FaqItem question="Можно отменить подписку?">
        В любой момент. Никаких автопродлений без согласия, никаких скрытых платежей. После отмены оставшиеся
        дни оплаченного периода остаются доступны.
      </FaqItem>
      <FaqItem question="А если я работодатель?">
        У нас есть тариф Employer — публикация вакансий + доступ к кандидатам со скрин-резюме. См. <a href="/employers" class="text-landing-accent-start hover:underline">страницу для работодателей</a>.
      </FaqItem>
    </div>
  </div>
</section>
```

Не забыть импорт в frontmatter: `import FaqItem from "../components/FaqItem.astro";`

- [ ] **Step 3: Commit**

```bash
git add apps/landing
git commit -m "feat(landing): FAQ section with 5 common questions"
```

---

## Task 6: Standalone-страницы — `/pricing`, `/employers`, `/about`

Эти страницы дублируют разделы homepage детальнее. SEO-оптимизированные, индексируемые отдельно.

**Files:**
- Create: `apps/landing/src/pages/pricing.astro`
- Create: `apps/landing/src/pages/employers.astro`
- Create: `apps/landing/src/pages/about.astro`

- [ ] **Step 1: /pricing**

`apps/landing/src/pages/pricing.astro`:

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
import PricingCard from "../components/PricingCard.astro";
import FaqItem from "../components/FaqItem.astro";

const tiers = [/* тот же массив что на homepage; вынести в src/lib/tiers.ts если хочется DRY */];
---

<BaseLayout title="Тарифы — Proshli" description="Простые и понятные тарифы. Free навсегда, Pro за ₽490/мес, Employer за ₽4 900/мес.">
  <section class="py-32 px-6">
    <div class="mx-auto max-w-6xl">
      <h1 class="text-48 md:text-72 font-extrabold tracking-tight text-center mb-4">Тарифы</h1>
      <p class="text-16 text-landing-text-muted text-center mb-16 max-w-xl mx-auto">Без скрытых платежей, отмена в один клик.</p>
      <div class="grid md:grid-cols-3 gap-6 mb-24">{tiers.map((t) => <PricingCard {...t} />)}</div>

      <div class="border-t border-white/5 pt-16">
        <h2 class="text-24 font-semibold text-center mb-8">Часто задают</h2>
        <div class="space-y-3 max-w-3xl mx-auto">
          <FaqItem question="Что входит в Free?">3 AI-запроса в день, еженедельный дайджест, базовый match-score.</FaqItem>
          <FaqItem question="Как работает биллинг?">Через ЮKassa. Принимаем карты, СБП, ЮMoney. Чек на email.</FaqItem>
          <FaqItem question="Возврат?">В течение 14 дней — полный возврат. После — пропорционально оставшимся дням.</FaqItem>
        </div>
      </div>
    </div>
  </section>
</BaseLayout>
```

Вынести `tiers` в `apps/landing/src/lib/tiers.ts` если на homepage уже есть копия — DRY. Тогда импорт `import { tiers } from "../lib/tiers";`.

- [ ] **Step 2: /employers**

`apps/landing/src/pages/employers.astro`:

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
import FeatureCard from "../components/FeatureCard.astro";

const features = [
  { icon: "🎯", title: "Кандидаты с match-score", description: "Видишь сразу процент совпадения между требованиями вакансии и резюме кандидата." },
  { icon: "⚡", title: "Скрининг за минуту", description: "AI делает first-pass: отсеивает явно нерелевантных, оставляет топ-5." },
  { icon: "👥", title: "Команда до 5", description: "Включено в тариф. Дополнительные места — ₽490 за каждого." },
];
---

<BaseLayout title="Для работодателей — Proshli" description="AI-скрининг кандидатов. Видишь только тех, кто реально подходит — без ручной разборки сотен резюме.">
  <section class="py-32 px-6">
    <div class="mx-auto max-w-6xl">
      <h1 class="text-48 md:text-72 font-extrabold tracking-tight text-center mb-4">Для работодателей</h1>
      <p class="text-18 text-landing-text-muted text-center mb-16 max-w-2xl mx-auto">
        AI делает first-pass за HR. Ты видишь только тех, кто реально подходит.
      </p>
      <div class="grid md:grid-cols-3 gap-6 mb-24">{features.map((f) => <FeatureCard {...f} />)}</div>

      <div class="rounded-2xl bg-gradient-to-br from-landing-accent-start/20 to-landing-accent-end/10 border border-landing-accent-start p-12 text-center shadow-glow">
        <h2 class="text-32 font-bold mb-4">Готов пробовать?</h2>
        <p class="text-14 text-landing-text-muted mb-6">14 дней бесплатно. Без карты на старте.</p>
        <a href="https://app.proshli.ru/employer/onboarding" class="inline-block rounded-lg h-11 leading-[2.75rem] px-8 bg-gradient-to-r from-landing-accent-start to-landing-accent-end text-white font-medium">Начать триал</a>
      </div>
    </div>
  </section>
</BaseLayout>
```

- [ ] **Step 3: /about**

`apps/landing/src/pages/about.astro`:

```astro
---
import BaseLayout from "../layouts/BaseLayout.astro";
---

<BaseLayout title="О Proshli">
  <section class="py-32 px-6">
    <div class="mx-auto max-w-3xl prose prose-invert">
      <h1 class="text-48 md:text-72 font-extrabold tracking-tight text-center mb-12">О нас</h1>
      <p class="text-18 text-landing-text-muted leading-loose">
        Proshli — это попытка решить «job-search fatigue» в IT. Слишком много вакансий, слишком много шума,
        слишком много copy-paste-описаний. Мы делаем AI-фильтр, который читает вакансии за тебя и шлёт только
        релевантные матчи.
      </p>
      <h2 class="text-24 font-semibold mt-12 mb-4">Команда</h2>
      <p class="text-14 text-landing-text-muted leading-loose">
        Сейчас это solo-проект (привет, я Alex). Делаю в свободное от Sherlock Taxi support вечером и по выходным.
        Если интересно — пиши в Telegram: <a href="https://t.me/" class="text-landing-accent-start hover:underline">@proshli_contact</a>.
      </p>
      <h2 class="text-24 font-semibold mt-12 mb-4">Технически</h2>
      <p class="text-14 text-landing-text-muted leading-loose">
        Стек: Python (FastAPI, async SQLAlchemy, Celery), Next.js + Astro фронт, Anthropic Claude для AI,
        Postgres + pgvector, всё развёрнуто на одном VPS с Caddy. Код частично открыт — следи за блогом.
      </p>
    </div>
  </section>
</BaseLayout>
```

- [ ] **Step 4: Commit**

```bash
git add apps/landing/src/pages/pricing.astro apps/landing/src/pages/employers.astro apps/landing/src/pages/about.astro
git commit -m "feat(landing): standalone pricing, employers, about pages"
```

---

## Task 7: Блог через Content Collections

**Files:**
- Create: `apps/landing/src/content/config.ts`
- Create: `apps/landing/src/content/blog/ai-vs-handcraft.md`
- Create: `apps/landing/src/content/blog/how-it-works.md`
- Create: `apps/landing/src/content/blog/digest-vs-search.md`
- Create: `apps/landing/src/pages/blog/index.astro`
- Create: `apps/landing/src/pages/blog/[...slug].astro`
- Create: `apps/landing/src/layouts/BlogLayout.astro`

- [ ] **Step 1: Content collection schema**

`apps/landing/src/content/config.ts`:

```typescript
import { defineCollection, z } from "astro:content";

const blog = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishDate: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog };
```

- [ ] **Step 2: 3 затравочных поста**

`apps/landing/src/content/blog/how-it-works.md`:

```markdown
---
title: "Как Proshli находит твои матчи: технически"
description: "Embedding резюме, cosine similarity, semantic ranking — что под капотом."
publishDate: 2026-05-26
tags: ["engineering", "ai"]
---

Когда ты загружаешь резюме, на сервере происходит следующее:

1. **Извлечение текста.** PDF/DOCX парсится через `pypdf` / `python-docx`. Если резюме на скане — fallback на OCR (Tesseract).
2. **Embedding.** Текст резюме (≤8000 символов) идёт в embedding-модель — получаем 1024-мерный вектор. Сейчас используем Claude embedding (если будет дешевле OpenAI text-embedding-3-large, переключимся).
3. **Хранение.** Вектор кладётся в Postgres с pgvector. На каждую новую вакансию мы тоже считаем embedding (заголовок + первые 500 символов описания).
4. **Match-score.** При показе списка вакансий считаем cosine similarity между твоим резюме и каждой вакансией: `1 - (resume <=> vacancy)`. Шкала 0-100%.

Дальше — пороги: 80+ показываем как high-match, 60-80 как relevant, ниже — без бейджа. Можно фильтровать.

Подробнее в [архитектурном документе](https://github.com/...) (когда-нибудь откроем код).
```

`apps/landing/src/content/blog/ai-vs-handcraft.md`:

```markdown
---
title: "Почему AI-поиск лучше ручных фильтров"
description: "Ручные фильтры умирают на пересечениях. AI — нет."
publishDate: 2026-05-23
tags: ["product"]
---

Классический job-board даёт тебе чекбоксы: «Backend», «Senior», «Москва или удалёнка». Это работает, пока:

- Ты знаешь точное название роли (а Data Engineer и ML Engineer пересекаются)
- Ты знаешь, какой стек тебе нужен (а вакансия с Go может быть в команде на Rust)
- Ты не против листать 200 результатов

AI понимает контекст: «я backend-senior на Go, но готов рассмотреть Rust, если команда сильная, и платформенные задачи интереснее CRUD». Это запрос, который не сводится к чекбоксам.

Сейчас AI у нас — Anthropic Claude через streaming chat. Tool-calls возвращают релевантные карточки. Дальше — твой клик.
```

`apps/landing/src/content/blog/digest-vs-search.md`:

```markdown
---
title: "Digest vs active search: что выбрать"
description: "Не каждый ищет работу прямо сейчас. Для пассивного поиска digest лучше."
publishDate: 2026-05-20
tags: ["product"]
---

Большинство людей в IT не ищут работу активно — но открыты к интересным предложениям. Для этой группы AI-поиск не нужен. Нужен digest:

- Раз в день / раз в неделю
- Только high-match вакансии (80%+)
- В Telegram, без email-спама
- Можно ставить на паузу

Это бесплатно навсегда. AI работает в background — ты ничего не нажимаешь.

Активный поиск с AI-чатом включается, когда ты решаешь «всё, ищу». Тогда Pro — ₽490/мес — даёт безлимит запросов и daily digest.
```

- [ ] **Step 3: BlogLayout**

`apps/landing/src/layouts/BlogLayout.astro`:

```astro
---
import BaseLayout from "./BaseLayout.astro";
import type { CollectionEntry } from "astro:content";

interface Props { post: CollectionEntry<"blog"> }
const { post } = Astro.props;
const formattedDate = post.data.publishDate.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
---

<BaseLayout title={`${post.data.title} — Proshli Blog`} description={post.data.description}>
  <article class="mx-auto max-w-3xl px-6 py-24">
    <a href="/blog" class="text-13 text-landing-text-muted hover:text-landing-text-primary">← Все статьи</a>
    <h1 class="text-32 md:text-48 font-extrabold tracking-tight mt-6 mb-3">{post.data.title}</h1>
    <p class="text-13 text-landing-text-muted mb-12">{formattedDate}</p>
    <div class="prose prose-invert prose-lg max-w-none">
      <slot />
    </div>
  </article>
</BaseLayout>
```

- [ ] **Step 4: Blog index**

`apps/landing/src/pages/blog/index.astro`:

```astro
---
import { getCollection } from "astro:content";
import BaseLayout from "../../layouts/BaseLayout.astro";

const posts = (await getCollection("blog", ({ data }) => !data.draft)).sort(
  (a, b) => b.data.publishDate.valueOf() - a.data.publishDate.valueOf(),
);
---

<BaseLayout title="Блог — Proshli" description="Заметки о том, как мы строим Proshli и что узнаём по дороге.">
  <section class="mx-auto max-w-3xl px-6 py-24">
    <h1 class="text-48 font-extrabold tracking-tight mb-12">Блог</h1>
    <div class="space-y-8">
      {posts.map((post) => (
        <a href={`/blog/${post.slug}`} class="block rounded-xl border border-white/10 bg-white/[0.02] p-6 hover:border-landing-accent-start/40 transition-colors">
          <h2 class="text-20 font-semibold mb-2">{post.data.title}</h2>
          <p class="text-14 text-landing-text-muted leading-loose mb-3">{post.data.description}</p>
          <div class="flex items-center gap-3 text-12 text-landing-text-muted">
            <span>{post.data.publishDate.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" })}</span>
            {post.data.tags.length > 0 && <span>·</span>}
            {post.data.tags.map((t) => <span class="px-2 py-0.5 rounded-full border border-white/10">{t}</span>)}
          </div>
        </a>
      ))}
    </div>
  </section>
</BaseLayout>
```

- [ ] **Step 5: Blog detail (dynamic route)**

`apps/landing/src/pages/blog/[...slug].astro`:

```astro
---
import { getCollection, type CollectionEntry } from "astro:content";
import BlogLayout from "../../layouts/BlogLayout.astro";

export async function getStaticPaths() {
  const posts = await getCollection("blog", ({ data }) => !data.draft);
  return posts.map((post) => ({ params: { slug: post.slug }, props: { post } }));
}

interface Props { post: CollectionEntry<"blog"> }
const { post } = Astro.props;
const { Content } = await post.render();
---

<BlogLayout post={post}>
  <Content />
</BlogLayout>
```

- [ ] **Step 6: Запустить и проверить**

`pnpm dev` → `/blog/` показывает 3 поста, `/blog/how-it-works/` рендерит markdown в красивой типографике.

- [ ] **Step 7: Commit**

```bash
git add apps/landing
git commit -m "feat(landing): blog content collections with 3 seed posts"
```

---

## Task 8: Dockerfile + GitHub Actions

**Files:**
- Create: `apps/landing/Dockerfile`
- Modify: `.github/workflows/build-and-push.yml`

- [ ] **Step 1: Dockerfile**

`apps/landing/Dockerfile`:

```dockerfile
# Multi-stage build для Astro static output.
# Финальный image — nginx:alpine с предсобранным dist/.

# --- Stage 1: build ---
FROM node:22-alpine AS builder

WORKDIR /workspace

# pnpm через corepack (без npm i -g)
RUN corepack enable && corepack prepare pnpm@10.10.0 --activate

# Копируем lockfile + workspace конфиг
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./

# Копируем зависимые packages
COPY packages/design-tokens/package.json packages/design-tokens/
COPY packages/tsconfig/package.json packages/tsconfig/

# Копируем landing
COPY apps/landing/package.json apps/landing/

# Установка
RUN pnpm install --frozen-lockfile --filter @proshli/landing...

# Копируем всё остальное и билдим
COPY packages packages
COPY apps/landing apps/landing

RUN pnpm --filter @proshli/landing build

# --- Stage 2: nginx serve ---
FROM nginx:1.27-alpine

COPY --from=builder /workspace/apps/landing/dist /usr/share/nginx/html
COPY apps/landing/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

`apps/landing/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Astro generates clean URLs by default, fallback to index.html for SPA-like routing isn't needed
    # since all pages are pre-rendered. But add fallback for 404 page.
    error_page 404 /404.html;

    # Static assets — long cache
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # HTML — short cache, revalidate
    location / {
        try_files $uri $uri/index.html $uri.html =404;
        add_header Cache-Control "public, max-age=300, must-revalidate";
    }
}
```

- [ ] **Step 2: GitHub Actions**

В `.github/workflows/build-and-push.yml` добавить landing job. Прочитать существующий workflow, добавить новый job или новую matrix-запись.

Если matrix — добавить `landing` к списку:

```yaml
strategy:
  matrix:
    app: [api, web, workers, tgbot, landing]
```

И обновить step «Build and push» — context должен включать `apps/landing/`, image-tag `proshli-landing:latest`.

- [ ] **Step 3: Локальный build-тест**

```bash
cd /c/Users/Alex/Cursor/jobskout
docker build -f apps/landing/Dockerfile -t proshli-landing:dev .
docker run -p 8080:80 --rm proshli-landing:dev
```

Открыть `http://localhost:8080/` — должна работать homepage.

- [ ] **Step 4: Commit**

```bash
git add apps/landing/Dockerfile apps/landing/nginx.conf .github/workflows/build-and-push.yml
git commit -m "ops(landing): Dockerfile + nginx config + CI matrix entry"
```

---

## Task 9: docker-compose.prod.yml + Caddy переключение

**Files:**
- Modify: `deploy/docker-compose.prod.yml` — добавить `proshli-landing` service
- Modify: `deploy/Caddyfile` — `proshli.ru` теперь указывает на landing-контейнер

- [ ] **Step 1: docker-compose.prod.yml — новый service**

В `deploy/docker-compose.prod.yml` добавить:

```yaml
  landing:
    image: ${LANDING_IMAGE}
    container_name: proshli-landing
    restart: unless-stopped
    networks:
      - proshli-internal
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost/"]
      interval: 30s
      timeout: 5s
      retries: 3
```

В `.env.prod.example` добавить:

```
LANDING_IMAGE=cr.yandex/PROD_REGISTRY/proshli-landing:latest
```

- [ ] **Step 2: Caddyfile — переключение `proshli.ru` на landing**

В `deploy/Caddyfile`:

Заменить блок `proshli.ru` так, чтобы reverse_proxy шёл на `proshli-landing:80` (вместо текущего `proshli-web:3000`).

```caddyfile
proshli.ru, www.proshli.ru {
    encode gzip zstd
    reverse_proxy proshli-landing:80 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
    log { output stdout; format json }
}
```

Блок `app.proshli.ru` (добавленный в Phase 0) остаётся указывать на `proshli-web:3000` — пока без изменений (рерайт случится в Phase 2).

- [ ] **Step 3: Локальный smoke с docker-compose**

```bash
cd /c/Users/Alex/Cursor/jobskout
# Подменить LANDING_IMAGE на локальный build
LANDING_IMAGE=proshli-landing:dev docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d landing caddy
curl -H "Host: proshli.ru" http://localhost:80/
```

Expected: HTML главной страницы Astro.

- [ ] **Step 4: Commit**

```bash
git add deploy/docker-compose.prod.yml deploy/.env.prod.example deploy/Caddyfile
git commit -m "ops(prod): add proshli-landing service + route proshli.ru to Astro"
```

---

## Task 10: Деплой в прод

Это критический шаг — переключаем главную страницу на новый стек.

- [ ] **Step 1: Pre-deploy чек-лист**

- [ ] DNS-запись `app.proshli.ru` указывает на VPS IP (создать заранее, минимум за 6 часов)
- [ ] `LANDING_IMAGE` env var добавлена в `deploy/.env.prod` на сервере
- [ ] Прод `make smoke-prod` зелёный сейчас
- [ ] Phase 0 завершена и задеплоена (AI guardrails фикс)

- [ ] **Step 2: Push в main + дождаться CI**

```bash
git push origin main
# Подождать ~7 минут пока CI билдит и пушит образ proshli-landing:latest
```

Проверить в Yandex Container Registry: образ появился.

- [ ] **Step 3: Pull + up на сервере**

На VPS (через `plink` или SSH):

```bash
cd /opt/proshli
git pull
# Pull нового образа landing
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod pull landing
# Up landing (запускаем впервые)
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d landing
# Caddy reload (без даунтайма)
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod restart caddy
```

- [ ] **Step 4: Smoke-test**

```bash
make smoke-prod
# Дополнительно:
curl -s https://proshli.ru/ | head -20
# Expected: HTML с заголовком "AI читает вакансии, ты не читаешь"

curl -s -o /dev/null -w "%{http_code}\n" https://proshli.ru/pricing
# Expected: 200

curl -s -o /dev/null -w "%{http_code}\n" https://app.proshli.ru/
# Expected: 200 (Next.js всё ещё отвечает на app subdomain)
```

- [ ] **Step 5: Lighthouse-проверка**

```bash
npx lighthouse https://proshli.ru/ --only-categories=performance,accessibility,best-practices,seo --quiet
```

Targets:
- Performance: ≥90 (target ≥95)
- Accessibility: ≥95
- Best Practices: ≥95
- SEO: ≥95

Если performance <90 — проверить:
- Размер JS bundle (Astro показывает на билде; не должен быть >50KB на главной кроме islands)
- Lazy-load островов (`client:visible` / `client:idle` для тех, что не critical)
- Размер изображений (использовать `<Image>` Astro для оптимизации)

- [ ] **Step 6: Mark Phase 1 completed**

В `docs/superpowers/specs/2026-05-26-frontend-million-design.md`:

```markdown
### Phase 1 — Astro landing (Weeks 2-3) ✅ COMPLETED 2026-MM-DD
```

```bash
git add docs/superpowers/specs/2026-05-26-frontend-million-design.md
git commit -m "docs(spec): mark Phase 1 (Astro landing) as completed"
git push
```

---

## Risks & Mitigations

1. **Tailwind v4 vs v3 несовместимость с preset из `@proshli/design-tokens`.** Если Astro 5 ещё не поддерживает Tailwind v4 в момент старта Phase 1 — остаёмся на v3 для landing. Tokens preset работает с обеими версиями, поскольку он использует `theme.extend` (v3 API), а v4 это совместимо.

2. **Spline runtime 200KB+.** В Step 3 Task 3 мы используем минимальный SVG-grid backdrop вместо Spline. Это даёт Lighthouse 95+ без жертв. Если хочется реального 3D — добавить Spline после Phase 1 launch как отдельный PR, с `client:visible` чтобы не блокировать FCP.

3. **Demo-stream «не выглядит как AI».** Если визитёры жалуются что демо очевидно фейк — добавить: typing-indicator перед каждой карточкой («AI ищет в Yandex...»), randomize порядок появления, varying delays. Не делаем сейчас, делаем по фидбеку после launch.

4. **Шрифты Inter Variable отсутствуют локально.** Скачать с https://rsms.me/inter/files/Inter.var.woff2 и положить в `apps/landing/public/fonts/`. В `BaseLayout.astro` добавить:

   ```html
   <link rel="preload" as="font" type="font/woff2" href="/fonts/Inter.var.woff2" crossorigin />
   ```

   И `@font-face` в `global.css`.

5. **MDX vs Markdown.** Затравочные посты — простой markdown. Если позже потребуется встраивать React-компоненты в посты — переименовать `.md` → `.mdx`. Astro MDX integration уже включена в `astro.config.mjs`.

6. **Внутренние ссылки на `app.proshli.ru` сломаны до Phase 2.** Сейчас Header ссылается на `https://app.proshli.ru/auth/login`. Если в момент Phase 1 launch DNS-запись `app.proshli.ru` ещё не создана — ссылки приведут на ошибку. **Обязательное условие:** DNS `app.proshli.ru` создаётся ДО Phase 1 step 10 (deploy).

7. **Caddy reload может занять >5 секунд если certificate автоматически перевыпускается.** Подготовить план отката: если `curl https://proshli.ru/` возвращает ошибку — `docker compose ... restart caddy` второй раз обычно фиксит.

---

## Definition of Done

- [ ] `https://proshli.ru/` показывает новый Astro лендинг
- [ ] `https://proshli.ru/{pricing,employers,about,blog}` все возвращают 200 и корректно отрендерены
- [ ] `https://proshli.ru/blog/how-it-works/` отрендерил markdown
- [ ] Hero AI-демо работает: ввёл запрос → 3 карточки появились с анимацией
- [ ] Lighthouse mobile: Performance ≥90, A11y ≥95, BP ≥95, SEO ≥95
- [ ] `https://app.proshli.ru/` всё ещё работает (текущий Next.js)
- [ ] `make smoke-prod` зелёный
- [ ] Phase 1 отмечена в spec как `✅ COMPLETED`

Готов к старту Phase 2 (Next.js app shell rewrite).
