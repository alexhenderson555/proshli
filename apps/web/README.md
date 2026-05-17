# Otklik.ai Web (Next.js)

## Что делает

Веб-интерфейс монорепы Otklik.ai: лендинг, поиск вакансий, профили
соискателя/работодателя, AI-чат. Next.js App Router, Tailwind v4,
shadcn-tokenизированная дизайн-система.

## Установка

```bash
cd apps/web
pnpm install
```

Минимум переменных окружения (`.env.local`):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

См. полный список в `apps/web/.env.example`. Валидация — через
`@t3-oss/env-nextjs` (`apps/web/lib/env.ts`): отсутствие или неверный
формат значения роняет билд громко, а не превращается в `undefined`
во время рантайма.

## Команды

```bash
pnpm dev          # next dev на :3000
pnpm build        # next build (standalone output для Docker)
pnpm lint         # eslint
pnpm type-check   # tsc --noEmit
pnpm test         # playwright e2e
```

## Структура

| Путь | Назначение |
|------|------------|
| `app/` | App Router — страницы и layout |
| `components/` | Локальные UI-примитивы (Button/Card/Badge/…) |
| `features/` | Feature-папки (`ai-chat/` со streaming SSE-клиентом) |
| `lib/` | `api.ts`, `env.ts`, `cn.ts`, `session.ts` |

## Траблшутинг

| Проблема | Что проверить |
|----------|----------------|
| Нет данных / 404 от API | Бэкенд запущен, верный `NEXT_PUBLIC_API_URL` |
| CORS | API настроен с `cors_allow_origins`, схема http/https совпадает |
| Сборка падает | Node 20+, чистая установка через `pnpm install --frozen-lockfile` |

Документация Next.js: [nextjs.org/docs](https://nextjs.org/docs).
