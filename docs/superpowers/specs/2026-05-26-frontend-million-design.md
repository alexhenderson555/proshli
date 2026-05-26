# Frontend Rewrite — «Миллион из 10» Design Spec

**Status:** Draft, ready for plan
**Date:** 2026-05-26
**Author:** Alex + Claude (brainstorming session)

---

## Goal

Поднять фронт Proshli до уровня «топ-1% в индустрии» — премиальный UX, который продаёт сам себя через лендинг и не утомляет в ежедневной работе. Backend, ingest, AI, биллинг — не трогаем (стабильны и работают в проде по адресу `proshli.ru`). Фронт делим на два инструмента, каждый под свою задачу.

Ключевые ожидания:

- **Лендинг** — Vercel/Geist-grade wow с первой секунды. AI-демо как hero, тонкая 3D-подложка. Конверсия из «зашёл» в «загрузил резюме».
- **Приложение** — Linear-style сдержанность. Cmd+K везде, AI всегда под рукой (Cmd+J), gen-UI карточки вакансий прямо в чате. Без gradient-овой усталости на каждом экране.
- **Adjacent quality** — параллельные backend-фиксы, без которых лендинг продаёт «продукт, который режет английские запросы» и «бота, который тупит на кнопках».
- **Anti-AI-slop voice** — лендинг **ни на одной странице** не должен выглядеть как ИИшная страница. Иначе аудитория (айтишники, опытные пользователи) раскусит и закроет вкладку. См. секцию ниже.

---

## Voice & Anti-Slop Rules (НЕ нарушать ни на одной странице)

Аудитория Proshli — IT-профессионалы, которые видят 100 SaaS-сайтов в неделю и за 3 секунды узнают шаблонный AI-визуал. Если они почувствуют «это нагенерили в Lovable/V0», доверие испарится и они закроют вкладку. Это **критерий приёмки**, не «nice to have».

### Визуальные anti-tells

**Не делать:**

- ❌ **Центрированный hero** «заголовок + подзаголовок + центральный CTA-button» — самый частый AI-визуал. Сдвинуть hero влево, поставить CTA не в очевидное место, разбить симметрию.
- ❌ **3 одинаковые карточки с emoji-иконками** (📄🎯📬, ⚡🔒🚀, etc.) в секции «Как работает». Это базовый AI-pattern. Заменить на: ассиметричный layout с одной большой иллюстрацией + 3 коротких пояснения сбоку; или custom-нарисованные SVG-иконки (не из Heroicons / Lucide); или вообще без секции «How it works» — показать процесс через анимированный демо.
- ❌ **Gradient text на каждом заголовке.** Использовать максимум 1 раз на странице — в hero. Остальные заголовки — однотонные.
- ❌ **«Trusted by» logo bar** если нет реальных кастомеров. Cringe-сигнал.
- ❌ **Идеально-симметричные сетки.** Карточки разных размеров, нерегулярные отступы, off-grid элементы — это «hand-touched».
- ❌ **Stock-фото / AI-аватарки команды** — лучше совсем без фото, чем сгенерённые.
- ❌ **Lottie-анимации с generic «успехом».** Слишком узнаваемо.
- ❌ **Чекмарки `✓` в pricing-фичах** одинаковыми кружочками. Использовать typography (em-dashes, indents), не bullet-list.

**Делать:**

- ✅ **Асимметрия в layout** — hero сдвинут, текстовые блоки разной ширины, элементы выходят за «безопасную» сетку.
- ✅ **Custom-детали** — нестандартные разделители (не `<hr>`, а текстовый «—  —  —» или dashed-линия с разрывами), нерегулярные углы скругления, mono-шрифт для подписей где не очевидно.
- ✅ **Editorial-моменты** — где-то крупная цитата без украшений, где-то параграф в 2 колонки, где-то pull-quote сбоку. Как в журнале, не как в Figma-шаблоне.
- ✅ **Реальные скриншоты** интерфейса вместо мокапов или диаграмм.
- ✅ **Технические детали с числами** — `12,847 вакансий`, `embedding 1024-мерный вектор`, `cosine similarity > 0.85` — это сигнал «писал инженер», а не «нагенерил GPT».

### Голос текста (копирайт)

**Запрещённые формулировки** (мгновенно палят AI):

- «Discover your next opportunity» → ❌
- «Powered by AI» → ❌ (зашквар, везде есть)
- «Seamless / effortless / unleash / elevate / harness» → ❌
- «Trusted by thousands» (без пруфов) → ❌
- «Revolutionary / cutting-edge / state-of-the-art» → ❌
- Generic «We believe...» / «Our mission is to...» → ❌
- Любые «We» в solo-проекте → ❌, использовать «Я»

**Чем заменить:**

- ✅ **Solo-founder voice от первого лица.** «Я задолбался листать hh каждый день и сделал AI, который читает за меня. Сейчас он работает на 12 847 вакансиях из ~50 источников. Это бета — пиши, если что-то сломалось».
- ✅ **Конкретика, не абстракция.** Вместо «AI matches your skills» — «AI берёт твой текст резюме, считает embedding (1024-мерный вектор), сравнивает с такими же векторами вакансий через cosine similarity, ранжирует по убыванию. На запросе `Go senior remote от 500К` сейчас даёт 23 матча выше 80%».
- ✅ **Идиомы, ругательства (умеренно), self-deprecation.** «hh — это уже не больно, но всё ещё скучно». «Если ты HR — извини, ты тут не клиент». «Сделано двумя руками за вечера, баги ждать стоит».
- ✅ **Технические термины без перевода.** «embedding», «cosine similarity», «match-score» — IT-аудитория не нуждается в переводе. Перевод палит «писал маркетолог».
- ✅ **Короткие предложения, неровный ритм.** Не «In a world where job-seeking is increasingly complex, we...» а «Вакансий слишком много. Слишком одинаковых. Решение: AI делает first-pass.»

### Контент

- ✅ **Реальный блог** от автора с реальными мыслями, не «10 tips for...». Заметка типа «Почему я выбрал pgvector а не Pinecone и пожалел» лучше любого маркетинга.
- ✅ **Open-source signals** — ссылки на свой GitHub, упоминание stack-а с конкретными версиями («FastAPI 0.115 + asyncpg + Anthropic Claude Sonnet 4.7»).
- ✅ **Прозрачность про ошибки** — «бета», «иногда AI ошибается, в этом случае нажми "пожаловаться"», открытая `/changelog` страница с реальными коммитами.

### Acceptance check для каждой страницы

Перед merge каждый PR с landing-страницей проходит самопроверку:

1. **3-second test:** покажи скриншот другому айтишнику без контекста на 3 секунды. Если первая реакция «это AI», страница не прошла.
2. **Word search:** `grep -i "discover\|seamless\|effortless\|powered by ai\|unleash\|revolutionary\|cutting-edge" page.html` — должно быть 0 матчей.
3. **Emoji audit:** в feature/how-it-works секциях — 0 emoji в роли иконок. Допустимы emoji только в personal-tone-блоках («Сделано в России 🇷🇺» — ОК).
4. **Centered-hero audit:** если первая страница — text-center + кнопка по центру + ничего больше — провал.
5. **Symmetry audit:** если все 3 секции homepage имеют одинаковую структуру (заголовок + 3 одинаковых карточки + CTA) — провал.

---

## Архитектура

### Структура монорепо

```
proshli/
├── apps/
│   ├── landing/        ← НОВОЕ: Astro 5 + React islands (proshli.ru)
│   ├── web/            ← REWRITE: Next.js 16 (app.proshli.ru)
│   ├── api/            ← БЕЗ ИЗМЕНЕНИЙ
│   ├── workers/        ← БЕЗ ИЗМЕНЕНИЙ
│   └── tgbot/          ← без UI-изменений, см. Adjacent Quality Fixes
├── packages/
│   ├── ui-v2/          ← НОВОЕ: design-system, React-primitives
│   ├── design-tokens/  ← НОВОЕ: CSS-vars + JSON для Astro + Next.js
│   ├── shared-types/   ← БЕЗ ИЗМЕНЕНИЙ (OpenAPI-gen)
│   └── ui/             ← DEPRECATE: оставляем до полной миграции, потом удаляем
└── deploy/
    └── Caddyfile       ← UPDATE: добавляем host-routing для landing
```

### Routing на проде

```
proshli.ru          → Caddy → proshli-landing  (Astro)
app.proshli.ru      → Caddy → proshli-web      (Next.js)
api.proshli.ru      → Caddy → proshli-api      (FastAPI)
```

Два web-контейнера, два docker image, два билда в CI. Это даёт:

- **Полная независимость билдов** — landing деплоится за 30 секунд (статика), Next.js — отдельным шагом.
- **Astro может быть пиксель-перфект без Next.js middleware** — никакой борьбы за SSG vs RSC, никаких next-intl на 200KB JS на маркетинговой странице.
- **A/B-тесты лендинга безопасны** — приложение никогда не падает из-за регрессии маркетинга.

**Альтернатива (отвергнута):** Один Next.js с двумя путями (`/` для лендинга, `/app/*` для приложения). Минусы: размер бандла, общая модель данных, маркетинг под Next-opinion.

---

## Tech Stack

### `apps/landing/` (Astro 5)

| Слой | Выбор | Зачем |
| --- | --- | --- |
| Фреймворк | Astro 5 (Server Islands, View Transitions) | MPA-first, минимум JS, идеальный Lighthouse |
| Islands | `@astrojs/react` | реюз React-компонентов из `packages/ui-v2` |
| Стиль | Tailwind v4 + design-tokens | единая палитра с app |
| 3D / Hero | Spline (export → glTF, react-three-fiber) | дешевле Three.js с нуля, дизайнер-friendly |
| Анимации | Framer Motion (для islands) | hover/scroll/enter |
| AI-демо | Server-side stream к `api.proshli.ru/ai/chat/stream` | прямой fetch, парсим SSE на клиенте |
| Контент | Astro Content Collections | блог и кейсы как MD/MDX, type-safe |
| i18n | Astro `@astrojs/i18n` | RU дефолт, `/en/...` зеркало |
| SEO | `@astrojs/sitemap`, OG-images через `og-image-generator` | автогенерация на билде |
| Аналитика | Plausible (self-hosted, оставшийся хвост Sprint 1) | без cookie-баннеров |

### `apps/web/` (Next.js 16)

Оставляем Next.js — для аутентифицированных экранов RSC + Server Actions всё ещё лучшее API. Но **переписываем layout shell** и **подменяем UI-библиотеку** под новый design system.

| Слой | Выбор | Зачем |
| --- | --- | --- |
| Фреймворк | Next.js 16 (App Router, RSC) | то же что сейчас, без переезда |
| UI primitives | `packages/ui-v2` (custom поверх Radix UI) | shadcn-vibe но pixel-perfect под Linear-эстетику |
| Стиль | Tailwind v4 + design-tokens | синк с landing |
| Анимации | Framer Motion + tiny custom hooks | micro-interactions, без overcooking |
| Cmd+K | `cmdk` (paco/cmdk) | де-факто стандарт, keyboard-first |
| Cmd+J (AI side-panel) | custom + `useChat` от ai-sdk | реюз стриминга, side-sheet через Radix Dialog |
| Gen-UI карточки в чате | `ai/rsc` + `streamUI` (Vercel AI SDK) | RSC компоненты в чате, type-safe |
| PWA | `next-pwa` (Workbox) + `@vercel/og` для иконок | offline-кеш + push |
| Push | Web Push API + VAPID | без сторонних сервисов |
| Темы | `next-themes` | оставляем 4 темы (light/dark/system/oled) |
| i18n | `next-intl` | оставляем |
| Auth / API | существующий `lib/api.ts` + JWT в cookie | без изменений |

### `packages/design-tokens/`

Файл-формат — JSON manifest + сгенерированные CSS custom properties + Tailwind preset.

```
packages/design-tokens/
├── tokens.json          ← single source of truth
├── build.ts             ← компилирует в:
├── dist/
│   ├── tokens.css       ← :root { --color-bg-primary: ... }
│   ├── tokens.js        ← export const tokens = {...}
│   └── tailwind.ts      ← preset для Tailwind v4
```

Категории токенов: `color`, `spacing` (4px base), `radius` (4/6/8/12/16/24), `font` (family + size + weight + line-height), `motion` (duration + easing), `shadow`, `z-index`.

### `packages/ui-v2/`

React-компоненты на Radix UI primitives (то же ядро что у shadcn). Список:

- **Primitives:** Button, Input, Textarea, Select, Checkbox, Radio, Switch, Slider, Tooltip, Popover, Dialog, Sheet, Toast, DropdownMenu, ContextMenu, Tabs, Accordion, Progress
- **Composites:** VacancyCard (новая Linear-style), Pill, KbdShortcut, MatchPill (мигрируем), Avatar, EmptyState, ErrorBoundary, LoadingState, SkeletonLine
- **Layout:** AppShell (sidebar + top-bar + main), CommandPalette, SidePanel, EmptyDashboard, OnboardingStep
- **Marketing-only (для landing):** GradientText, HeroChat, FeatureCard, PricingCard, TestimonialCard, ParticleBackdrop

Все компоненты — controlled, без внутреннего state. Дизайн-токены пробрасываются через CSS-vars (а не через theme-props), это даёт работу в Astro islands без React Context.

---

## Information Architecture

### Landing (`proshli.ru`)

| Путь | Цель | Wow-elements |
| --- | --- | --- |
| `/` | Hero AI-demo + value props + how-it-works + pricing + FAQ + CTA | particle backdrop, gen-UI cards в hero |
| `/employers` | Лендинг для работодателей | split-view "соискатель vs работодатель" |
| `/pricing` | Тарифы (free / pro / employer) | A/B сравнение, FAQ |
| `/about` | Миссия, команда, контакты | минималистичный, фотографии |
| `/blog/[slug]` | Кейсы, гайды, новости | content collections |
| `/legal/{privacy,terms,oferta}` | Юридические страницы | без дизайна, читаемая типографика |
| `/en/...` | Зеркало на английском | то же содержимое |

### App (`app.proshli.ru`)

| Путь | Изменения относительно сегодня |
| --- | --- |
| `/auth/login` | Redesign под Vercel-vibe, добавляем passkey-кнопку (если поддерживается браузером) |
| `/auth/register` | То же + magic-link через email опция |
| `/auth/onboarding` | **НОВОЕ:** Step wizard — upload резюме → AI извлекает skills → 3 matched вакансии за 60 сек |
| `/` (dashboard) | **REDESIGN:** match-digest hero + recent vacancies + быстрые действия (apply, save, set digest) |
| `/vacancies` | Список + sticky filter sidebar + Cmd+J side-panel для AI |
| `/vacancies/[id]` | Detail: фиксим текущие UX-проблемы (пустые поля прячем, парсинг зарплат) |
| `/applications` | **REDESIGN:** Kanban-доска (saved/applied/interviewing/offer/rejected) |
| `/resume` | Builder с live-preview |
| `/resume/versions/[id]` | Каждая версия — diff с предыдущей, AI-improve кнопка |
| `/settings/{account,notifications,billing,integrations}` | Tabbed layout, integrations показывают Telegram-link статус |
| `/employer/*` | Без UI-изменений в текущей итерации (см. Out of Scope) |

### Глобальные элементы

- **Cmd+K** — глобальный палитра: search vacancies, navigate, set theme, log out
- **Cmd+J** — открыть AI side-panel (slide-in справа)
- **Кнопка «?»** в header — keyboard shortcuts cheat sheet
- **Toast в правом нижнем углу** — feedback на сейв/apply

---

## Design System

### Цветовая палитра

**Landing (Vercel/Geist vibe):**

```
--color-bg-primary:    #0a0a0a
--color-bg-secondary:  linear-gradient(160deg, #0a0a0a 0%, #1a0b2e 70%, #3b1956 100%)
--color-accent-start:  #7c3aed  (фиолетовый)
--color-accent-end:    #a855f7
--color-text-primary:  #ffffff
--color-text-muted:    rgba(255,255,255,0.6)
--color-glow:          rgba(124, 58, 237, 0.35)
```

**App (Linear vibe):**

```
--color-bg-primary:    #0a0a0b
--color-bg-secondary:  #19191c
--color-bg-tertiary:   #2a2a30  (sidebar)
--color-border:        #1c1c22
--color-accent:        #5e6ad2  (Linear-purple)
--color-text-primary:  #e6e6e9
--color-text-muted:    #9a9aa3
--color-text-subtle:   #7a7a82
```

**Светлая тема (app, обязательная):**

```
--color-bg-primary:    #f7f7f8
--color-bg-secondary:  #ffffff
--color-border:        #e4e4e7
--color-accent:        #5e6ad2  (тот же фиолет)
--color-text-primary:  #18181b
--color-text-muted:    #71717a
```

OLED-тема (`oled`): тот же app, но `--color-bg-primary: #000`. System-тема следует системе.

### Типографика

- **Sans:** Inter Variable (font-feature-settings: `'cv11', 'ss01', 'ss03'`)
- **Mono:** JetBrains Mono Variable (для kbd, code, brutalist-акцентов)
- **Размеры:** 11 / 12 / 13 / 14 / 16 / 18 / 20 / 24 / 32 / 48 / 72
- **Веса:** 400 / 500 / 600 / 700 / 800
- **Line-height:** tight 1.1, normal 1.5, loose 1.75
- **Letter-spacing:** -0.03em на 32+, -0.02em на 18-24, 0 на 14-, 0.06-0.18em на caps-labels

### Spacing & Radius

- **Spacing:** 4px base — 1/2/3/4/6/8/10/12/16/20/24/32/40/48/64/80
- **Radius:** 4 (small), 6 (input/button), 8 (card), 12 (sheet/dialog), 16 (hero-block), 999 (pill)

### Motion

- **Duration:** instant 100ms, fast 150ms, normal 250ms, slow 400ms, lazy 600ms
- **Easing:** `cubic-bezier(0.16, 1, 0.3, 1)` — Apple-like exit
- **Defaults:** hover 150ms, dialog enter 250ms, list item enter 100ms staggered
- **Reduced-motion:** отключаем всё, кроме opacity-fade на 100ms

### Shadow

- **xs:** `0 1px 2px rgba(0,0,0,0.05)`
- **sm:** `0 2px 8px rgba(0,0,0,0.08)`
- **md:** `0 4px 16px rgba(0,0,0,0.12)`
- **lg:** `0 12px 32px rgba(0,0,0,0.18)`
- **glow:** `0 0 32px var(--color-glow)` (только для landing)

---

## Key Flows

### 1. Landing AI Hero Demo

**Цель:** через 5 секунд после захода юзер видит, что AI работает, и сам хочет зарегистрироваться.

```
┌──────────────────────────────────────────────────────────────┐
│  Proshli                              EN   Войти   Регистрация│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│     ┌─ particle backdrop (Spline / r3f, 60fps) ─┐            │
│     │                                            │            │
│     │     AI читает вакансии,                    │            │
│     │     ты не читаешь                          │            │
│     │     ─────────────────────                  │            │
│     │     ┌────────────────────────────────┐     │            │
│     │     │ "Backend в Москву от 400К"     │ ↵   │            │
│     │     └────────────────────────────────┘     │            │
│     │                                            │            │
│     │  ─ AI стримит: ─                           │            │
│     │  ┌──── Yandex · Platform        94% ──┐    │            │
│     │  │ Go · Kafka · Remote · ₽550K        │    │            │
│     │  └────────────────────────────────────┘    │            │
│     │  ┌──── Tinkoff · CoreBank       89% ──┐    │            │
│     │  │ Go · Postgres · Hybrid · ₽600K     │    │            │
│     │  └────────────────────────────────────┘    │            │
│     │                                            │            │
│     │  [Зарегистрируйся, чтобы получать дайджест]│            │
│     └────────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

**Технически:**

- Hero — React island, gradient + Spline scene в background (`z-index: -1`)
- Чат-input — controlled, отправляет на `POST api.proshli.ru/ai/chat/stream`
- SSE-frame `data-content` → накапливаем текст; `data-card` → новая карточка с анимацией enter
- Демо-режим: backend получает флаг `?demo=true` → отдаёт 3 заготовленные карточки + поясняющий текст, чтобы:
  - не съедать AI-бюджет анонимных юзеров
  - гарантировать качество демо (не зависит от живых вакансий)
  - быстрая отдача (<500ms total)
- Анимация карточек — staggered enter с Framer (`initial: { y: 20, opacity: 0 }`, `delay: index * 0.1`)
- CTA-кнопка появляется после 3-й карточки, scroll к ней мягкий

**Метрика успеха:** % посетителей, доскролливших до hero-CTA, конвертирующихся в регистрацию. Цель — 4-7% (baseline для SaaS-лендингов).

### 2. App Cmd+K Command Palette

**Цель:** power-user никогда не лезет мышью.

Триггер: `Cmd+K` (Mac) / `Ctrl+K` (Win). Открывается dialog c full-text search:

- **Sections:** Vacancies (top 5 match-score), Actions (apply / save / set-digest-daily / log-out / toggle-theme), Pages (navigate to /vacancies, /resume, /settings/...), Recent (последние 5 просмотренных)
- **Keyboard:** ↑↓ для навигации, Enter — выбор, Tab — pin section, Esc — закрыть
- **Поиск backend:** debounced 150ms запрос на `/vacancies?q=...&limit=10&include_match=true`
- **Empty state:** «Нажми ↓ или начни печатать»

Библиотека: [`cmdk`](https://cmdk.paco.me/) от paco — де-факто стандарт.

### 3. App Cmd+J AI Side-Panel

**Цель:** AI всегда под рукой, без переключения страниц.

Триггер: `Cmd+J` / `Ctrl+J`. Из правого края въезжает sheet (480px wide):

```
┌─────────────────────────┐
│  AI Assistant      ✕    │
├─────────────────────────┤
│  History  ▾             │
│                         │
│  ─ Ты ────────────────  │
│  "Backend Go от 500К"   │
│                         │
│  ─ AI ────────────────  │
│  Нашёл 8 вакансий по... │
│  ┌─ Yandex · 94% ─────┐ │
│  │ Go · Kafka · ₽550K │ │
│  └────────────────────┘ │
│  ┌─ Tinkoff · 89% ────┐ │
│  │ Go · Postgres      │ │
│  └────────────────────┘ │
│                         │
│  Расскажи про первую?   │
│                         │
├─────────────────────────┤
│  > Напиши сообщение...  │
└─────────────────────────┘
```

- Реализация: Radix Dialog в side-mode + custom slide-in анимация
- Стрим из существующего `/ai/chat/stream` (SSE) — backend не трогаем
- **Gen-UI:** карточки рендерятся через Vercel AI SDK `streamUI` + RSC. Клик по карточке открывает `/vacancies/[id]` в новой вкладке (или embedded preview)
- **History:** список последних 10 разговоров, сохраняются в localStorage + sync с backend через `/ai/chat/history` (новый endpoint, см. Adjacent Fixes)
- **Контекст-aware:** если открыта страница `/vacancies/123`, sidepanel предлагает «Спросить про эту вакансию»

### 4. Gen-UI карточки в чате

**Цель:** AI отвечает не только текстом, но и кликабельными карточками, миниатюрами резюме, графиками.

Архитектура:

- Backend: `LLMService.stream_chat` в FastAPI уже умеет в tool-calls. Расширяем tool-set:
  - `render_vacancy_card(vacancy_id: int)` — отдаёт фронту маркер `{type: "vacancy-card", id: 123}`
  - `render_match_summary(scores: list[float])` — sparkline
  - `render_resume_diff(resume_version_id: int)` — diff view
- Frontend: парсит SSE-фреймы `data-ui` с JSON-описанием компонента, рендерит соответствующий React-компонент из `packages/ui-v2/marketing` / `app`
- Type safety: shared-types генерит из OpenAPI описания tool-результатов

### 5. Onboarding wizard

**Цель:** «60 секунд до первого матча». Конверсия в активного юзера.

Шаги:

1. **Upload резюме** — drag-n-drop PDF/DOCX или `Ctrl+V` чтобы вставить текст. Уже работает в API (`POST /resumes`), нужен только новый UI.
2. **AI извлекает** — спинер на 5-15 сек, фоновый job, AI парсит skills + experience. Параллельно `embed` для match-score.
3. **Confirm/edit** — extracted данные показаны как pills, кликом редактируешь или удаляешь.
4. **Set preferences** — 3 вопроса: формат (remote/office/hybrid), уровень (junior/middle/senior/lead), желаемая зарплата (slider).
5. **Show 3 matches** — карточки с match-score 80+. CTA «Получать дайджест в Telegram» / «Получать email». Skip → дашборд.

UI — full-screen multi-step wizard с прогресс-баром и keyboard navigation (Enter → next, Esc → previous).

### 6. PWA

- **Manifest:** имя «Proshli», icons (192/512), `display: standalone`, theme-color matches accent
- **Service worker:** Workbox через `next-pwa`
  - precache: shell (`/`, `/vacancies`, `/dashboard`)
  - runtime cache: `api.proshli.ru/vacancies*` (NetworkFirst, 5-min ttl), `api.proshli.ru/health` (StaleWhileRevalidate)
  - offline fallback: показываем последний кеш + баннер «Оффлайн, синхронизация при возврате»
- **Push:** Web Push API + VAPID keys (генерим один раз, кладём в env), backend отправляет уведомления через `pywebpush`
  - Триггеры: новый match-score >85%, новое сообщение от employer, заявка перешла в interview
  - Юзер opt-in через `/settings/notifications`
- **Install prompt:** показываем на 2-м визите если в Chrome/Edge

### 7. Адаптивность

- **Mobile-first** для landing, **desktop-first** для app (но всё работает на phone)
- **Breakpoints:** `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`, `2xl: 1536px`
- **Cmd+K на мобиле:** заменяется на кнопку в bottom-bar
- **Cmd+J на мобиле:** AI sheet занимает 100% экрана
- **Vacancy detail на мобиле:** sticky bottom CTA (как сейчас, оставляем), но redesigned

---

## Adjacent Quality Fixes (backend / bot)

Не «фронт», но без них «миллион из 10» рассыпается. Делаем параллельно с фронт-рерайтом.

### A. AI guardrails — расширение CAREER_KEYWORDS

**Файл:** `apps/api/app/services/ai_guardrails.py:23-39`

**Проблема:** Любой английский запрос с ролью (`system analyst`, `data scientist`, `devops engineer`, `qa lead`) отвергается. Whitelist содержит русские слова + только 3 английских (`python`, `frontend`, `backend`).

**Решение:** Двухуровневая проверка:

1. **Расширить whitelist** — добавить ~80 английских IT-ролей: `analyst`, `developer`, `engineer`, `manager`, `designer`, `qa`, `devops`, `sre`, `data`, `ml`, `ai`, `scientist`, `lead`, `principal`, `staff`, `intern`, `fullstack`, `full-stack`, `architect`, `tech`, `team`, `cto`, `pm`, `product`, `ux`, `ui`, `react`, `vue`, `angular`, `node`, `golang`, `rust`, `kotlin`, `swift`, `ios`, `android`, `mobile`, `web`, `cloud`, `aws`, `gcp`, `azure`, `kubernetes`, `docker`, `linux`, `sql`, `nosql`, etc.
2. **Fallback на LLM-judge** — если whitelist не сработал, делаем дешёвый запрос к Haiku-3.5: «Это профессиональный/карьерный запрос? yes/no». Результат кешируем в Redis на 24 часа по hash(query). Cost ~$0.0001 per check.
3. **Telemetry** — логируем все rejects с текстом запроса, чтобы видеть false positives и доразвивать whitelist.

### B. Ingest spam filter

**Проблема:** на сайте появляются объявления о продаже крякнутого Windsurf за 500 звёзд, фейковые «работы из дома». TG-prefilter гейтит только публикацию в наш канал, но НЕ блокирует попадание в БД и на сайт.

**Решение:** новый сервис `apps/api/app/services/spam_filter.py`, запускается в worker при ingest **до** записи в `vacancies`. Логика:

1. **Heuristics (быстро, 99% случаев):**
   - Слова-маркеры: `crack`, `кряк`, `обход лимит`, `звёзд за`, `unlimited trial`, `интерцептор`, `подмена пакетов`, `обход подписки`
   - Подозрительная зарплата: `от X до Y RUB` где Y < 100 (вряд ли реальная вакансия)
   - Контакт «ЛС/@telegram-handle» без названия компании
   - Длина текста <100 символов + наличие emoji-спама (🔥, 💎, 🚀 >5 раз)
2. **LLM-judge на borderline случаях:** Haiku-3.5 с промптом «Это легитимная вакансия или продажа товара/услуги/спам? Ответь: vacancy/spam/unsure». Cached.
3. **Action:** при spam=true — НЕ вставляем в `vacancies`, логируем в `rejected_ingest` (новая таблица для аудита).

### C. Bot callback instant-ack

**Файл:** `apps/tgbot/handlers.py` — все ~15 `@dp.callback_query` handlers

**Проблема:** `query.answer()` вызывается **после** HTTP-запроса к API. Telegram крутит спиннер на кнопке до момента ack, юзер видит лаг = roundtrip + DB-op.

**Решение:** универсальный pattern для всех handlers:

```python
@dp.callback_query(F.data.startswith("ch_approve_"))
async def channel_approve(query: CallbackQuery, http: httpx.AsyncClient) -> None:
    await query.answer()  # ack СРАЗУ, спиннер исчезает
    # ... валидация ...
    status, body = await post_channel_decision(http, "approve", candidate_id, ...)
    # результат — отдельным сообщением или edit_message_text
    if status == 200:
        await query.message.edit_text(f"✅ Запланировано: {body.get('detail')}")
    else:
        await query.message.edit_text(f"❌ Ошибка ({status})")
```

Альтернатива для случаев где надо показать toast — `query.answer("⏳", show_alert=False)` сразу, потом `bot.answer_callback_query(query.id, text="✅", show_alert=False)` (не работает, нельзя дважды). Поэтому либо instant-ack + edit message, либо instant-ack + send new message.

### D. Salary parser

**Проблема:** Парсер берёт первое попавшееся `$X-Y` или `от X до Y` из текста как зарплату. В постах типа «вечный триал за $20-60 в месяц подписки» это даёт «зарплата 20-60 RUB».

**Решение:** контекстный парсер в `apps/api/app/services/vacancy_parser.py`:

1. Искать зарплату только в строках с маркерами: `зарплата`, `оклад`, `вилка`, `salary`, `compensation`, `ЗП`, `payment`
2. Если в одной строке несколько чисел — брать ближайшее к маркеру
3. Распознавать валюту: `₽`, `RUB`, `USD`, `$`, `EUR`, `€`. Если `$X` или `USD X` — конвертировать в RUB по фиксированному курсу на ingest day (или оставлять USD как отдельное поле)
4. Sanity check: если `salary_max < 30_000 RUB` или `> 5_000_000 RUB` — null, не показывать на UI (это либо ошибка парсинга, либо нерелевантно)

---

## Phasing (План на 9 недель)

Все недели — solo dev, ~10-15 часов/неделя.

### Phase 0 — Foundation (Week 1)

1. `packages/design-tokens` — токены + build script
2. `packages/ui-v2` — skeleton, первые 5 primitives (Button, Input, Dialog, Sheet, Tooltip)
3. Caddy config с subdomain routing (`app.proshli.ru`, `proshli.ru`)
4. Adjacent fix A (AI guardrails whitelist) — quick win, разлочивает English queries сразу

### Phase 1 — Astro landing (Weeks 2-3)

1. Init `apps/landing/` с Astro 5, Tailwind v4
2. Hero AI demo (компонент + demo-режим backend)
3. Pricing, Employers, About, FAQ
4. Blog (content collections, 2-3 затравочных поста)
5. Dockerfile, GitHub Actions для build+push
6. Deploy: добавить контейнер `proshli-landing`, Caddy роутит `proshli.ru` сюда

### Phase 2 — App shell rewrite (Weeks 4-6)

1. AppShell в `packages/ui-v2`: sidebar + top-bar + main
2. Cmd+K (cmdk) с full search + actions
3. Cmd+J AI side-panel (Radix Dialog + sheet-mode + SSE consumer)
4. Theme system: light/dark/system/oled, мигрирует с текущего next-themes setup
5. Миграция страниц: dashboard → vacancies (list + detail) → applications

### Phase 3 — Key features (Weeks 7-8)

1. Gen-UI карточки в чате (backend tool-calls + frontend rendering)
2. Onboarding wizard (full-screen multi-step)
3. PWA: manifest, service worker, push subscription UI
4. Adjacent fix B (ingest spam filter) — после того как BD-схема для `rejected_ingest` готова
5. Adjacent fix C (bot callback instant-ack) — refactor всех handlers
6. Adjacent fix D (salary parser)

### Phase 4 — Polish & Launch (Week 9)

1. Lighthouse audit: landing 95+, app 90+ на mobile
2. A11y audit: WCAG 2.1 AA, focus management в Cmd+K и dialog'ах
3. Push notifications smoke test
4. Switch DNS: `proshli.ru` → новый landing, `app.proshli.ru` → новый Next.js
5. Старый `apps/web` — снести (или оставить как archive ветку)

---

## Out of Scope (Phase 2)

Намеренно НЕ делаем сейчас:

- **`/employer/*`** — UI не редизайним, остаётся текущий (employer'ов пока единицы, низкий приоритет)
- **Native mobile app** — PWA покрывает 95% use cases, нативное приложение откладываем до 1000+ DAU
- **Realtime SSE дашборд** — обсуждали B-вариант с бейджами, но это перфоманс-overhead на solo-deployed Redis. Откладываем
- **Saved searches + email/push алерты** — overlap с digest-функцией, не нужны
- **Resume builder с темплейтами** — текущий «версионный» подход оставляем, темплейт-маркетплейс — Phase 2
- **Self-hosted Sentry / Plausible** — оставшийся хвост Sprint 1, делаем когда будет инфра-окно (не блокирует launch)
- **Тёмная тема для лендинга «по умолчанию»** — лендинг всегда тёмный по дизайну
- **B/D vibe options** — не используем AI-native (B) как основной UI приложения, не используем Brutalist (D) вообще

---

## Open Questions / Risks

1. **Spline vs кастомный Three.js для hero 3D.** Spline — быстро, но 200KB+ runtime. r3f с самописной сценой — больше работы, но контролируемый размер. **Решение:** начинаем со Spline-prototype, мерим Lighthouse → если падает ниже 90 — переходим на r3f.

2. **Astro и SSE для AI-демо.** Astro generally MPA, но AI-демо — клиентский React island со streaming. Надо убедиться что fetch к `api.proshli.ru/ai/chat/stream` работает через CORS (он должен быть открыт на API).

3. **Demo-режим backend для лендинга.** Новый параметр `?demo=true` на `/ai/chat/stream` — это новая фича API. Альтернатива: статически захардкоженные демо-карточки на лендинге без вызова API. **Решение:** хардкод на стороне Astro (3 заготовленные «вакансии» + симуляция стрима через `setTimeout`). Это убирает зависимость лендинга от API uptime.

4. **next-pwa + Next.js 16.** На момент написания not 100% compat. Возможно надо `@serwist/next` (форк) или ручная настройка Workbox через `next.config.mjs`. **Митигация:** Phase 3 начнём с PoC PWA, если `next-pwa` не работает — за час переходим на `@serwist/next`.

5. **Cost AI-judge для ingest spam-фильтра.** При 200 вакансий/день и ~30% borderline = 60 calls × $0.0001 = 0.6 цента/день. ОК. Если scale-up до 2000/день — стоит закешировать агрессивнее.

6. **Migration пользователей.** Старые сессии (JWT в cookie на `proshli.ru`) после переезда app на `app.proshli.ru` — куки не передадутся. **Решение:** в Caddy при переходе с `proshli.ru/app/...` редирект на `app.proshli.ru/...` с прокидыванием cookie через `Set-Cookie` на новом домене. Phase 4 (week 9) — детальная migration story.

7. **Brand identity / logo.** Текущий лого Proshli — простая «P» в фиолетовом квадрате. На уровне «миллион из 10» это не сработает. **Out of scope для этой спеки**, но Phase 4 включит «get a real designer for logo refresh» — иначе wow-лендинг ломается на лого.

---

## Success Criteria

Считаем достижением, если:

1. **Lighthouse:** landing 95+/95+/95+/95+, app 90+/95+/90+/90+ на mobile slow 4G
2. **First match in onboarding:** ≤60 секунд от загрузки резюме до показа 3 матчей
3. **AI side-panel:** Cmd+J → first token <800ms на корпоративном Wi-Fi
4. **PWA install rate:** >5% от mobile-юзеров
5. **English query support:** 0 false positives на whitelist для топ-50 IT-ролей
6. **Spam в БД:** ≤1 спам-вакансия в неделю проходит ingest (сейчас — несколько в день)
7. **Bot callback latency:** ≤200ms perceived (instant-ack) даже при медленном API

---

## References

- Vercel/Geist design: https://vercel.com/geist
- Linear UI: https://linear.app
- Astro 5 docs: https://docs.astro.build
- cmdk (Cmd+K): https://cmdk.paco.me
- Vercel AI SDK (gen-UI): https://sdk.vercel.ai/docs/ai-sdk-rsc
- next-pwa: https://github.com/shadowwalker/next-pwa
- Workbox: https://developer.chrome.com/docs/workbox
- AI guardrails баг location: `apps/api/app/services/ai_guardrails.py:23-39`
- Bot callback баг location: `apps/tgbot/handlers.py:477-522` (и ~15 других callback handlers)
- Текущая архитектура: `docs/architecture.md`
- Sprint 1 plan (для контекста — что уже сделано): `docs/superpowers/plans/2026-05-17-sprint-1-foundation.md`
