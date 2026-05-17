# Otklik.ai — Platform Design (V2, ребренд JobSkout)

**Дата:** 2026-05-17
**Статус:** Design (утверждён, переход в writing-plans)
**Автор:** Alex (с помощью ИИ-ассистента)
**Кодовая база:** существующий JobSkout MVP (FastAPI + Next.js + TG-бот) → переименовать и эволюционировать в Otklik.ai

**Бренд-решение (2026-05-17):** ребрендинг с JobSkout на **Otklik.ai**. Причины: (1) коллизия с американским dating-app Skout создаёт SEO/app-store-проблемы; (2) «Отклик» — нативное русское слово для ICP №1 с двойным смыслом (отклик соискателя ↔ response рекрутера); (3) уникально, легко регистрируется, премиальное звучание для «продукта 10/10». Доменное имя `otklik.ai` подлежит верификации до Sprint 1.

---

## 1. TL;DR

**Otklik.ai** — крупная итерация существующего JobSkout MVP до уровня премиум job-search платформы для IT-аудитории РФ и СНГ. Главные дифференциаторы относительно HH/Habr Career:

1. **Скоринг «шанс взятия»** — лента сортируется не по новизне, а по комбинации match × конкуренция × возраст × активность работодателя.
2. **Парсинг источников, которых нет у конкурентов** — Telegram-каналы + карьерные страницы крупных компаний (Сбер, Тинькофф, Яндекс, Авито, Ozon).
3. **AI-резюме под каждую вакансию** + cover letter + автоматический поиск контактов компании из открытых источников.
4. **AI-агенты для подготовки** — research-агент по компании, networking-агент, mock-интервью, salary negotiation coach.
5. **Workflow управления откликами** — канбан, авто follow-up, email-интеграция с автотрекингом статусов.

**Цель MVP:** запустить closed beta на 50-100 платящих пользователей через 12 недель, выйти на 1000 платящих юзеров через 6-9 месяцев.

---

## 2. Цели и не-цели

### Цели

- Premium-продукт «выглядящий на 10/10» — дизайн, UX и копирайт уровня лучших SaaS (Linear, Notion, Raycast).
- Полноценный freemium SaaS с реальной воронкой Free → Pro → Premium.
- Юридически чистая работа в РФ (152-ФЗ, реестр операторов ПД, локализация данных, маркировка рекламы).
- Уникальный inventory вакансий (Telegram + корпоративные сайты) как defensible moat.
- Стратегия унификации AI: дешёвая русская модель (YandexGPT) для массовых задач, премиум-модель (Claude/GPT) для критичных, всё через единый AI-роутер.
- Заложить фундамент для B2B-направления (Talent Pool) через 12+ мес.

### Не-цели (что НЕ делаем намеренно)

- Не делаем агрессивный автопилот, отправляющий отклики без подтверждения юзера — это путь к банам и репутационному ущербу.
- Не парсим закрытые/слитые базы контактов; работаем только с открытыми источниками.
- Не делаем геймификацию (стрики, бейджи) — выглядит несерьёзно для IT-аудитории.
- Не делаем видео-резюме (нишевая фича с низким спросом).
- Не пытаемся конкурировать с HH на их поле массовости — занимаем нишу «умнее за те же деньги».

---

## 3. Целевая аудитория

### ICP №1 (MVP-фокус)

**IT/digital специалисты РФ и СНГ:** разработчики (бэк/фронт/мобайл/DevOps), дизайнеры, продакт-менеджеры, аналитики данных, QA, ML-инженеры. Грейды middle и выше (платёжеспособная аудитория).

- Платёжеспособность: 600-2000₽/мес за SaaS-инструмент — норма.
- Каналы: Habr, Хабр Career, Telegram-каналы для разработчиков, YouTube IT-блогеры, vc.ru.
- Боль: на HH много шума, низкокачественные вакансии, фрод; время на отклики тратится впустую; нет нормального инструмента подготовки к интервью под конкретную компанию.

### ICP №2 (V2-расширение)

- IT-релоканты: ищут вакансии с релокацией или удалёнкой за рубежом.
- Junior IT (Free-тариф + курсы по реферальной программе).

### V3+ — экспансия

- IT в СНГ: Казахстан, Армения, Грузия.
- Англоязычный продукт под глобальный remote-рынок (более высокий чек $20-50/мес).

---

## 4. Полный feature-set

### 4.1 MVP (12 недель)

**Парсинг и каталог:**
- HH.ru (официальный API)
- Habr Career (GraphQL endpoint)
- Telegram-каналы (~30 IT-каналов через MTProto/Telethon)
- Корпоративные сайты (Сбер, Тинькофф, Яндекс, Авито, Ozon — в MVP минимум 5)
- Дедупликация между источниками (нормализация title + company + salary fingerprint)
- Полнотекстовый поиск с фильтрами через Meilisearch

**Скоринг и лента:**
- Match-score через эмбеддинги (multilingual-e5-large локально + pgvector)
- Формула «шанс взятия» = f(match%, отклики, возраст вакансии, активность работодателя)
- Ghost-job детектор: heuristics + LLM-классификатор для пограничных случаев

**Резюме:**
- Импорт из PDF/DOCX + ссылка на HH-профиль
- AI-парсинг в структурированный master CV
- AI-генерация резюме под вакансию (YandexGPT Pro для RU, Claude Sonnet для EN)
- Cover letter generation

**Контакты:**
- Парсинг сайтов компаний на email/телефоны
- Парсинг Habr Career-профилей сотрудников (открытые)
- TG-каналы компаний

**Workflow:**
- Канбан-трекер откликов (драг-дроп статусов)
- Email-интеграция (Gmail/Yandex OAuth) с автообновлением статусов по входящим
- Real-time alerts: TG-бот + web push (свежие вакансии в первый час публикации)
- Авто follow-up через 5 дней молчания
- Stealth-mode (фильтр текущего работодателя)

**Платежи и тарифы:**
- Free / Pro 690₽ / Premium 1990₽ (см. раздел 9)
- ЮKassa, рекуррентные подписки, one-time покупки
- 7-дневный триал Premium без карты

**Фронт:**
- Темы: light / dark / system / OLED
- i18n: RU + EN
- Дизайн-система 10/10 (см. раздел 8)
- Lighthouse 95+, a11y WCAG AA, адаптив

### 4.2 V2 (мес. 4-6)

- **Mobile App** (React Native + Expo) — push-уведомления, Tinder-swipe лента
- **AI mock-интервью** — Whisper STT + Claude вопросы + Yandex SpeechKit TTS
- **Research-агент по компании** в один клик (досье из 10+ источников за 30 сек)
- **Networking-агент** — поиск 3 сотрудников в открытых источниках + draft cold-message'ей
- **Релокация-сегмент:** Relocate.me, JustJoinIT, Otta, Wellfound, RemoteOK
- **Persona-based мульти-резюме** (N версий, AI подбирает оптимальную)
- **Reject reason analysis + карта слабых мест**
- **Salary negotiation coach** (после оффера)
- **Дашборд аналитики рынка** для юзера
- **Краудсорсинг интервью-вопросов + зарплат** (фундамент сетевого эффекта)

### 4.3 V3 (мес. 7-12)

- **B2B Talent Pool** (open-to-work юзеры → доступ для компаний, основной доход)
- **ML-скоринг** на собственных данных
- **Открытый data-портал «Зарплаты IT РФ»** (SEO, медиа-публикации)
- **Авто-блог** с AI-генерируемыми обзорами по нашим данным
- **API для пауэр-юзеров и интеграций** (Zapier, Make)
- **Notion / Obsidian sync**
- **Экспансия в СНГ** (Казахстан, Армения, Грузия)

### 4.4 V4+ (год 2+)

- Английский продукт под EU/global remote-рынок
- Партнёрки с курсами (Skillbox, Яндекс.Практикум, Stepik, OTUS) через gap-анализ
- ATS-интеграции для B2B (Greenhouse, Lever, Huntflow)

---

## 5. Технический стек

### Frontend

| Слой | Технология | Обоснование |
|---|---|---|
| Web framework | **Next.js 15** (App Router) + TypeScript | SSR для SEO (open data + контент-маркетинг), быстрый, кадры легко нанимать |
| Styling | **Tailwind CSS** + CSS variables | Утилитарный стиль, темы через токены |
| UI Kit | **shadcn/ui** + кастомные компоненты | Open-source, копируется в проект, кастомизируется до нуля |
| Animations | **Framer Motion** | Микро-анимации, page transitions, swipe-карточки |
| Themes | **next-themes** | light / dark / system / OLED без перезагрузки |
| i18n | **next-intl** | App Router-friendly, URL-локали (`/ru/...`, `/en/...`) |
| Server state | **TanStack Query** | Кэширование, оптимистичные мутации |
| Client state | **Zustand** | Минималистичный, без бойлерплейта |
| Forms | **React Hook Form** + **Zod** | Типизированные формы, валидация |
| Charts | **Recharts** или **visx** | Salary insights, market dashboard |
| Tables | **TanStack Table** | Канбан-fallback, аналитика |
| Toasts | **Sonner** | Современные неинтрузивные уведомления |
| Storybook | да | Дизайн-система как single source of truth |
| Fonts | Inter (UI) + Manrope (headings) | Subset, preload, no FOIT/FOUT |

### Backend

| Слой | Технология | Обоснование |
|---|---|---|
| API | **FastAPI** (Python 3.12) | Уже используется в существующем MVP, AI/ML экосистема в Python мощнее всего |
| ORM | **SQLAlchemy 2.0** (async) + **Alembic** | Уже в проекте, async-режим |
| Validation | **Pydantic v2** | Контракты, OpenAPI авто-генерация |
| DB main | **PostgreSQL 16** + **pgvector** | Уже используется, embedding-поиск без отдельного Qdrant |
| Cache + queues | **Redis 7** | Кэш, Celery broker, rate limiting |
| Workers | **Celery** | Парсинг, AI-генерация. Через 1 год миграция на **Temporal** |
| Search | **Meilisearch** | Простой, быстрый, relevance из коробки. Альтернатива Typesense |
| Analytics DB | **ClickHouse** | Аналитика зарплат, event tracking, market dashboard |
| Browser automation | **Playwright** (cluster) | Парсинг корп. сайтов с тяжёлым JS |
| Auth | **JWT** + magic link + OAuth (Yandex, Google) | Уже частично в существующем MVP |

### AI-стек

| Задача | Модель | Где запускается | Цена |
|---|---|---|---|
| Embeddings (матчинг) | `intfloat/multilingual-e5-large` | Локально (CPU/GPU worker) | Бесплатно |
| Базовая генерация RU (резюме, cover, дайджесты) | **YandexGPT Pro** | Yandex Cloud API | ~₽0.40/1k токенов |
| Премиум-генерация RU/EN (research, mock-интервью, networking) | **Claude Sonnet 4.6** | Через посредника (ProxyAPI / Vsegpt) | ~₽0.90/1k токенов (Sonnet pricing + наценка) |
| EN-резюме и cover (Premium) | **Claude Sonnet 4.6** | Через посредника | то же |
| Fallback | **GPT-4o** | Через посредника | ~₽1.20/1k токенов |
| STT (mock-интервью) | **Whisper Large v3** | Локально на GPU-воркере | Бесплатно |
| TTS (mock-интервью, V2) | **Yandex SpeechKit** | Yandex Cloud API | ~₽0.40/1k символов |

**AI-роутер:** единый внутренний API. Запрос приходит с типом задачи (e.g. `generate_resume_ru`, `research_company`) → роутер выбирает модель → fallback на резерв при сбое → логирует latency + cost в ClickHouse для оптимизации.

### Инфраструктура

| Компонент | Решение | Обоснование |
|---|---|---|
| Cloud | **Yandex Cloud** (основное) или **Selectel** | Резидент РФ → 152-ФЗ комплаенс |
| Compute | Managed K8s или Compute Cloud | Auto-scaling воркеров |
| DB | Managed Postgres for Yandex Cloud | Бэкапы, replicas, без боли |
| Object Storage | Yandex Object Storage (S3-compatible) | Резюме, аватары, экспорты |
| CDN | Yandex CDN | Статика Next.js, изображения |
| CI/CD | **GitHub Actions** | Уже используется |
| Monorepo | **Turborepo** | `apps/web`, `apps/api`, `apps/workers`, `apps/tgbot`, `packages/ui`, `packages/shared-types` |
| Observability | **Sentry** (self-hosted в РФ или GlitchTip) + **Plausible** (self-hosted) | Прайвеси, без передачи данных за рубеж |
| Logging | Loki + Grafana или Yandex Cloud Logging | Centralized logs |

### Платежи

| Компонент | Решение |
|---|---|
| Платёжный шлюз | **ЮKassa** (Сбер) или **Тинькофф Касса** |
| Модели | Подписки (рекуррент), one-time покупки |
| Бухучёт | Самозанятый → ИП на УСН → ООО (см. раздел 12) |
| AI-расходы | YandexGPT (акты + НДС), Claude/GPT через посредника (акты ProxyAPI) |

---

## 6. Архитектура

### 6.1 Высокоуровневая схема

```
┌──────────────────────────────────────────────────────────────┐
│  CLIENTS                                                      │
│  Next.js Web (SSR)   │   React Native (V2)   │   TG-бот       │
└──────────────┬───────────────────┬───────────────────┬─────────┘
               │                   │                   │
               ▼                   ▼                   ▼
        ┌──────────────────────────────────────────────────┐
        │  API Gateway (FastAPI, REST + SSE для real-time) │
        │  + JWT auth, Rate limiting, OpenAPI              │
        └──────────────┬───────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┬─────────────────┐
       ▼               ▼               ▼                 ▼
  ┌────────┐    ┌───────────┐   ┌──────────┐    ┌──────────────┐
  │ Core   │    │ Matching  │   │ AI       │    │ Workflow     │
  │ Module │    │ Engine    │   │ Router   │    │ (Kanban,     │
  │ (CRUD) │    │ (pgvector │   │ + agents │    │  Email,      │
  │        │    │  + ranker)│   │          │    │  Reminders)  │
  └────────┘    └───────────┘   └──────────┘    └──────────────┘
       │               │               │                 │
       └───────────────┴───────────────┴─────────────────┘
                              │
                  ┌───────────┴────────────┐
                  ▼                        ▼
            ┌─────────────┐         ┌─────────────┐
            │ PostgreSQL  │         │ Redis       │
            │ + pgvector  │◄────────┤ (cache +    │
            │ (main DB)   │         │  Celery)    │
            └─────────────┘         └──────┬──────┘
                  ▲                        │
                  │                        ▼
            ┌─────────────┐         ┌────────────────────────┐
            │ ClickHouse  │         │ Celery Workers         │
            │ (analytics) │         │ ┌────────────────────┐ │
            └─────────────┘         │ │ Parsers (HH, Habr, │ │
                  ▲                 │ │ TG, corp. sites)   │ │
                  │                 │ ├────────────────────┤ │
            ┌─────────────┐         │ │ AI Workers         │ │
            │ Meilisearch │         │ │ (resume, cover,    │ │
            │ (search)    │         │ │  research, etc.)   │ │
            └─────────────┘         │ ├────────────────────┤ │
                                    │ │ Email Parser       │ │
                                    │ │ (Gmail/Yandex)     │ │
                                    │ ├────────────────────┤ │
                                    │ │ Embedding Worker   │ │
                                    │ │ (e5-large)         │ │
                                    │ └────────────────────┘ │
                                    └────────────────────────┘
                                              │
                              ┌───────────────┼──────────────┐
                              ▼               ▼              ▼
                         ┌────────┐    ┌──────────┐   ┌──────────┐
                         │ HH API │    │ Habr     │   │ Telegram │
                         │        │    │ Career   │   │ MTProto  │
                         └────────┘    └──────────┘   └──────────┘
                                              │
                                              ▼
                                       ┌─────────────────┐
                                       │ Corp. sites     │
                                       │ (Playwright)    │
                                       └─────────────────┘
```

### 6.2 Принципы

1. **Modular monolith** на старте — все модули внутри одного бэкенд-репо с чёткими границами (Hexagonal-style). Микросервисы — позже, когда реально упрёмся в нагрузку.
2. **Парсеры — отдельные воркеры**, могут масштабироваться независимо. Каждый парсер имплементирует общий интерфейс `Parser.fetch() -> List[RawVacancy]`. Добавление нового источника — новый класс.
3. **AI-роутер** изолирует выбор модели от прикладного кода. Логика «использовать YandexGPT для X, Claude для Y» сосредоточена в одном месте.
4. **pgvector внутри Postgres** вместо отдельного Qdrant — простота, для нашего объёма (миллионы вакансий) хватит.
5. **ClickHouse отдельно** для аналитики — Postgres не загибается под аналитическими запросами.
6. **Real-time alerts через SSE** (не WebSocket) — проще, надёжнее через прокси/CDN.

### 6.3 Модули backend

- `core/` — пользователи, профили, авторизация, RBAC
- `vacancies/` — модель вакансии, нормализация, дедупликация
- `parsers/` — стратегии для HH, Habr Career, Telegram, корп. сайтов
- `matching/` — embedding-поиск, формула скоринга «шанс взятия»
- `ai/` — AI-роутер, агенты (resume, cover, research, networking, mock-interview)
- `workflow/` — канбан, статусы откликов, email-парсер, reminders
- `payments/` — ЮKassa интеграция, тарифы, лимиты
- `compliance/` — журнал ПД, согласия, экспорт/удаление по запросу
- `analytics/` — ClickHouse ingester, метрики, events
- `tgbot/` — Telegram-бот для alerts и интерактива

---

## 7. Модель данных

### 7.1 Основные таблицы (Postgres)

```
users                       — учётные записи
  id, email, telegram_id, created_at, role, subscription_tier

user_profiles               — master CV
  user_id, raw_resume_blob, parsed_json, embedding vector(1024),
  desired_salary_min/max, preferred_locations, skills[], stealth_companies[]

resume_versions             — persona-based варианты (V2)
  id, user_id, persona_label, parsed_json, embedding

vacancies                   — нормализованная вакансия
  id, fingerprint, title, company_id, salary_min/max, currency,
  location, remote_type, description, requirements[], published_at,
  responses_count, source, source_id, raw_payload_id, embedding,
  ghost_score, status

vacancy_sources             — раз-source запись (одна вакансия на N источниках)
  vacancy_id, source, source_id, url, fetched_at

raw_vacancies               — исходные payloads (уже есть в MVP)
  id, source, payload, fetched_at

companies                   — досье
  id, name, normalized_name, website, hh_id, habr_id,
  size_estimate, sector, summary, last_activity_at

company_contacts            — открытые контакты
  company_id, type (email/phone/tg/url), value, source_url, verified_at

applications                — отклики юзера
  id, user_id, vacancy_id, status, created_at, last_event_at,
  resume_version_id, cover_letter_text

application_events          — история статусов (канбан)
  id, application_id, event_type, payload, created_at

interview_questions         — краудсорсинг (V2)
  id, company_id, role_level, question, source_user_id, created_at

salary_reports              — краудсорсинг зарплат (V2)
  id, company_id, role, level, salary_amount, currency, year, user_id

email_integrations          — OAuth токены для Gmail/Yandex
  user_id, provider, refresh_token_encrypted, last_synced_at

payments                    — лог транзакций
  id, user_id, amount, currency, status, provider_payment_id, type
```

### 7.2 ClickHouse

```
events                      — все события юзера (для воронок, A/B)
  ts, user_id, event_name, properties (JSON), session_id

salary_market               — агрегированные зарплаты для дашборда
  date, role, level, location, p25, p50, p75, p90, count

ai_calls                    — логи AI-вызовов
  ts, user_id, model, task_type, tokens_in/out, cost, latency_ms
```

### 7.3 Meilisearch

- Index `vacancies`: поля для full-text (title, company, description), фасеты (location, remote, salary_range, level), фильтры (ghost_score, source).

---

## 8. Frontend и дизайн-система (10/10)

### 8.1 Принципы дизайна

- **Premium-look уровня Linear / Raycast / Notion** — щедрая типографика, плотная сетка, минималистичные акценты.
- **Тёмная тема — дефолт для IT-аудитории**, но light/system/OLED доступны.
- **Анимации с характером** — не «крутящаяся загрузка», а Framer Motion с pruning при `prefers-reduced-motion`.
- **Каждый экран продуманный** — empty states с CTA, skeleton loaders, inline-валидация, optimistic UI.

### 8.2 Дизайн-токены

```
Spacing:    4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 96 (px) — 8pt grid
Typography: Inter 12/14/16/18/20/24/32/48; Manrope 24/32/48 (для H1/H2)
Colors:     OKLCH-палитра, primary / accent / muted / destructive / warning / success
Radius:     2 / 4 / 6 / 8 / 12 / 16 (px), default 8px
Shadows:    soft-1 (subtle borders), soft-2 (cards), soft-3 (modals/popovers)
Borders:    1px solid via CSS variables; в dark — тёплые серые
```

### 8.3 Темы

- `light` — base
- `dark` — OKLCH-инверсия, тёплые акценты
- `system` — следует ОС
- `oled` — true black `#000` для AMOLED-экранов
- Переключение без перезагрузки через `next-themes`
- Persists в localStorage + cookie (для SSR)

### 8.4 i18n

- `next-intl`, URL-локали `/ru/...` и `/en/...`
- Файлы переводов: `messages/ru.json`, `messages/en.json`
- Автодетект по `Accept-Language` при первом визите
- Юзер переключает явно — переключение запоминается в cookie
- Числа, даты, валюта — через `Intl.NumberFormat` / `Intl.DateTimeFormat`

### 8.5 Performance + accessibility

- Lighthouse 95+ на всех ключевых страницах (Performance, Accessibility, Best Practices, SEO)
- LCP < 2s, INP < 200ms, CLS < 0.1
- Image optimization через Next.js `<Image>` + WebP/AVIF
- Font subsetting + preload
- WCAG AA: контрастность, focus rings, keyboard nav, screen reader labels, `aria-*`
- `prefers-reduced-motion` уважается

### 8.6 Ключевые экраны

1. **Landing (SEO)** — RU + EN, social proof, демо без регистрации
2. **Demo wall (без регистрации)** — вставил ссылку на HH-профиль → видишь 10 лучших вакансий со скорингом, регистрируешься для большего
3. **Onboarding wizard** — резюме → желания → каналы alerts → готово (≤ 2 минуты)
4. **Лента вакансий** — карточки с score-бейджем, фильтры в боковой панели, swipe (на мобайл/RN)
5. **Карточка вакансии** — полное описание + match-breakdown + ghost-warning + кнопки «Подготовить отклик», «Открыть оригинал», «В избранное», «Скрыть»
6. **AI-резюме экран** — preview сгенерированного резюме и cover letter, редактируется inline, экспорт PDF
7. **Контакты компании** — найденные email/TG/сотрудники, CTA «открыть письмо в почтовом клиенте»
8. **Канбан** — drag-drop, фильтры, batch-операции
9. **Аналитика** — личный funnel + market dashboard (V2)
10. **Settings** — профиль, темы, язык, integrations, billing, privacy

---

## 9. Монетизация

### 9.1 Тарифы

| Фича | Free | Pro 690₽/мес | Premium 1990₽/мес |
|---|---|---|---|
| Лента со скорингом | 50/день | unlimited | unlimited |
| Real-time alerts | — | ✅ | ✅ priority (мин-1 после публикации) |
| AI-резюме | 3/неделю (YandexGPT) | unlimited (YandexGPT Pro) | unlimited (Claude/GPT-4o) |
| Cover letter | 3/неделю | unlimited | unlimited |
| Канбан-трекер | до 30 карточек | unlimited | unlimited |
| Email-автотрекинг | — | ✅ | ✅ |
| Поиск контактов | 1/неделю | 20/мес | unlimited |
| Автопилот «пакет дня» | — | до 10/день | до 30/день |
| Ghost detector | ✅ | ✅ | ✅ |
| Salary insights | базово | детально | детально + прогноз торга |
| Gap-анализ | — | 1/мес | unlimited |
| Research-агент | — | 5/мес | unlimited |
| Mock-интервью (V2) | — | — | 8/мес |
| Salary negotiation coach (V2) | — | — | ✅ |
| Networking-агент (V2) | — | — | ✅ |
| Stealth-mode | — | ✅ | ✅ |
| Релокация (V2) | — | ✅ | ✅ |
| Persona-резюме | 1 | 3 | unlimited |
| Auto follow-up | — | ✅ | ✅ |

### 9.2 One-time покупки

- Резюме + cover под 1 вакансию — 199₽
- Полное досье компании + контакты — 299₽
- 1 mock-интервью (V2) — 499₽

### 9.3 B2B (V3+)

- Talent Pool seat — 30 000₽/мес + комиссия за hire
- ATS-интеграции (V4)

### 9.4 Partner-кешбэк (V2+)

- Курсы Skillbox / Яндекс.Практикум / OTUS / Stepik по gap-анализу

### 9.5 Unit-economics (грубо)

| Метрика | Free | Pro | Premium |
|---|---|---|---|
| Costs/мес (AI + инфра) | ~30₽ | ~120₽ | ~450₽ |
| Цена | 0 | 690 | 1990 |
| Маржа | -30 | **570 (83%)** | **1540 (77%)** |

**Цель:** 1000 платящих юзеров через 6-9 мес → ~700к₽/мес валовой маржи.

### 9.6 Триал и анти-паттерны

- 7 дней Premium бесплатно при регистрации, **карта не требуется** для активации триала.
- Карта запрашивается явно, перед первым списанием. Автоматический даунгрейд в Free без сюрприза.
- Отписка в один клик, никаких retention dark patterns.
- Все лимиты Free прозрачно видны в UI («Осталось 2 из 3 AI-резюме на этой неделе»).

---

## 10. MVP-таймлайн (12 недель)

### Sprint 1 — нед. 1-2: Фундамент

- Yandex Cloud: VPC, Managed Postgres, Redis, S3
- Turborepo monorepo: `apps/web`, `apps/api`, `apps/workers`, `apps/tgbot`, `packages/ui`, `packages/shared-types`
- CI/CD на GitHub Actions: lint, type-check, тесты, build, deploy в staging
- Next.js 15 + Tailwind + shadcn + next-themes + next-intl скелет
- FastAPI скелет, Alembic-миграции (если есть из MVP — мигрируем), pgvector расширение
- Sentry, Plausible
- **Артефакт:** деплой staging «Hello World» + Storybook + дизайн-токены

### Sprint 2 — нед. 3-4: Парсеры + БД

- Полная схема БД (vacancies, companies, contacts, users, applications, события)
- **HH API parser** — официальный, полный
- **Habr Career parser** — GraphQL endpoint
- **Telegram parser** — Telethon, список 30 IT-каналов, пул аккаунтов, rate-limiting
- **Дедупликация** вакансий (fingerprint)
- pgvector + embedding-воркер (multilingual-e5-large на GPU-инстансе)
- Meilisearch индексация
- **Артефакт:** в БД 50к+ вакансий, поиск работает, дедуп работает

### Sprint 3 — нед. 5-6: Резюме + скоринг + ядро UI

- Импорт резюме (PDF / DOCX / HH-ссылка) → AI-парсинг → master CV
- Embedding резюме, match-score через pgvector
- Формула «шанс взятия»: match × age_factor × responses_factor × company_activity
- **Главный UI:** лента, фильтры, score-бейдж, темы, переключатель языка
- Карточка вакансии: полное описание + score-breakdown + CTA
- Auth: email + magic link + Yandex/Google OAuth
- **Артефакт:** юзер регится → импортирует резюме → видит ленту со скорингом

### Sprint 4 — нед. 7-8: AI + контакты + ghost detector

- AI-роутер (YandexGPT / Claude / GPT) с fallback и логированием в ClickHouse
- AI-генерация резюме под вакансию + cover letter (RU и EN)
- Поиск контактов: парсинг сайта компании + соц.сетей + Habr Career-профилей сотрудников
- Ghost-job детектор: heuristics + LLM-классификатор
- Salary insights v1 (по нашей же базе вакансий через ClickHouse-агрегаты)
- **Артефакт:** клик «Подготовить отклик» → готовое резюме + письмо + email компании

### Sprint 5 — нед. 9-10: Workflow

- Канбан-доска (Beautiful DnD или dnd-kit), шаблоны статусов
- Email-интеграция: подключение Gmail/Yandex по OAuth, парсинг входящих, авто-обновление статусов
- Real-time alerts: TG-бот для уведомлений + web push
- Авто follow-up через 5 дней молчания
- Stealth-mode (фильтр компаний и аффилированных юр.лиц)
- Gap-анализ резюме v1
- **Артефакт:** полный цикл от alert до офера в одном интерфейсе

### Sprint 6 — нед. 11: Платежи + комплаенс

- ЮKassa: подписки Pro/Premium, one-time покупки, рекуррент
- 152-ФЗ: политика, согласие, локализация данных в РФ
- Уведомление РКН об обработке ПД (подача документов параллельно — начали на нед. 6)
- Пользовательское соглашение, оферта, политика возвратов
- Welcome email-серия (transactional), базовая поддержка через TG
- **Артефакт:** юзер может купить, получить чек, отписаться в 1 клик

### Sprint 7 — нед. 12: Полировка + closed beta

- Багфиксы, UX-полировка, перфоманс (Lighthouse 95+)
- Корпоративные парсеры: Сбер, Тинькофф, Яндекс, Авито, Ozon (Playwright)
- Onboarding-туториал (продуктовая экскурсия)
- Open data dashboard (зарплаты IT) — публичная страница для SEO
- Запуск closed beta на 50-100 чел из своих сетей + анонс на Habr
- **Артефакт:** боевой релиз, первые платящие юзеры

### Буферы и риски (см. также раздел 13)

- ⚠️ Telegram-парсинг через MTProto → пул аккаунтов и rate-limiting. +3-5 дней буфера.
- ⚠️ 152-ФЗ оформление → подаём на 6-й неделе, не на 11-й. Параллельно с разработкой.
- ⚠️ Claude/GPT через прокси → начинаем с ProxyAPI/Vsegpt, армянское ИП — на год 2.
- ⚠️ Лимиты HH API → подаём заявку на whitelist через партнёрку.

---

## 11. Roadmap V2 / V3

### V2 (мес. 4-6 после запуска)

- Mobile app (React Native + Expo)
- AI mock-интервью (Whisper + Claude + Yandex SpeechKit)
- Research-агент по компании
- Networking-агент
- Релокация-сегмент (Relocate.me, JustJoinIT, Otta, Wellfound, RemoteOK)
- Persona-based мульти-резюме
- Reject reason analysis
- Salary negotiation coach
- Дашборд аналитики рынка для юзера
- Краудсорсинг интервью-вопросов и зарплат

### V3 (мес. 7-12)

- B2B Talent Pool
- ML-скоринг
- Открытый data-портал «Зарплаты IT РФ»
- Авто-блог по нашим данным
- API + Zapier/Make
- Notion / Obsidian sync
- Экспансия в СНГ

### V4+ (год 2+)

- Английский продукт под глобальный remote-рынок
- Курсы-партнёрки
- ATS-интеграции

---

## 12. Юридический комплаенс (РФ)

### 12.1 152-ФЗ (персональные данные)

- Регистрация оператора ПД в реестре Роскомнадзора (онлайн-заявление, 30 дней, бесплатно). Подаём на нед. 6.
- Локализация данных граждан РФ на серверах РФ (Yandex Cloud / Selectel закрывают).
- Согласие на обработку ПД при регистрации — отдельный чекбокс, не bundled с оффером.
- Политика обработки ПД — отдельная страница, индексируется.
- Журнал учёта ПД (Postgres-таблица + аудит-логи).
- Уведомление субъекта в течение 24 ч в случае утечки.
- DPO — Alex исполняет роль на ранних этапах (оформляется приказом).
- Право на удаление: кнопка «удалить аккаунт» с полным wipe'ом в 30 дней.

### 12.2 Парсинг чужих данных

- **HH.ru** — официальное API, договор о партнёрстве с программой интеграторов.
- **Habr Career** — GraphQL endpoint, rate-limit 1 req/sec, **не публикуем целиком — даём summary + ссылку на оригинал**.
- **Telegram** — публичные каналы, MTProto, юридически чисто. Указываем источник, если канал просит.
- **Корп. сайты** — публичная информация, robots.txt уважаем, 1 req/5 sec на домен.
- **Контакты сотрудников** — **только открытые источники** (сайт компании, публичные Habr Career-профили, открытые TG-каналы). Никаких слитых баз, никакого email-pattern guessing.

### 12.3 Договоры с юзерами

- Публичная оферта (заменяет договор B2C).
- Пользовательское соглашение.
- Политика конфиденциальности (связана с 152-ФЗ).
- Политика возвратов: после 1-го AI-запроса услуга оказана, возврат невозможен (явно в оферте).

### 12.4 Бизнес-формат

- **MVP:** самозанятый (НПД 6%) — лимит 2.4М₽/год выручки.
- **При росте:** ИП на УСН 6% (от 2.4 до 60М/год).
- **При 100+М/год или появлении инвестора:** ООО на ОСН или УСН-15%.

### 12.5 Налогообложение AI

- YandexGPT через ЮKassa — обычные расходы, НДС вычитается (для ИП с НДС / ООО).
- Claude/GPT через посредника (ProxyAPI/Vsegpt) — акт + чек в рублях, бухучёт работает.
- Прямые платежи Anthropic/OpenAI — не используются (не работает с РФ-картами без обхода).

### 12.6 Маркировка рекламы

- Все рекламные публикации с 2022 г. через ОРД (Vk, Yandex, ТГ-каналы).
- Учитываем в маркетинговом бюджете и пайплайне.

---

## 13. Риски и митигация

| Риск | Вероятность | Impact | Митигация |
|---|---|---|---|
| Бан HH API при росте | средняя | высокий | Партнёрство, whitelist, fallback на публичный поиск |
| Flood-баны TG-аккаунтов | высокая | средний | Пул из 5+ аккаунтов, rate-limit < 1 req/sec/account |
| Сбой ProxyAPI / Vsegpt | средняя | высокий | Мультипровайдер (2-3 посредника), автоматический failover |
| Изменение GraphQL Habr Career | средняя | средний | Snapshot-тесты парсера, alerting на drop в количестве вакансий |
| Изменение 152-ФЗ или новые требования | средняя | средний | Юрист на ретейнере (~15к₽/мес), мониторинг изменений |
| Конкурент копирует фичи | высокая | средний | Скорость + сетевые эффекты (краудсорсинг) — defensible moats |
| Дороговизна AI при scale | средняя | высокий | Локальные эмбеддинги, кэширование cover-шаблонов, prompt-caching на Claude |
| MVP не находит PMF | средняя | критический | Закрытая бета с интервью, итерации до запуска |

---

## 14. Метрики успеха

### MVP (12 недель)

- 50-100 регистраций в closed beta
- ≥ 30% активация (загрузка резюме + просмотр ленты)
- ≥ 10% конверсия trial → paid
- D7 retention ≥ 25%
- NPS ≥ 40

### 6 месяцев

- 1000 платящих юзеров
- ARPU ≥ 800₽/мес
- MRR ≥ 800к₽
- LTV/CAC ≥ 3
- Месячный churn ≤ 7%

### 12 месяцев

- 5000 платящих юзеров
- MRR ≥ 4М₽
- Запуск B2B Talent Pool (10+ компаний-клиентов)
- Public data dashboard приносит ≥ 30% органик-трафика

---

## 15. Решённые вопросы (по итогам ревью 2026-05-17)

1. ✅ **Название продукта** — ребрендинг на **Otklik.ai**. JobSkout остаётся внутренним кодовым именем существующего репо до Sprint 1, где делаем переименование (репо, домены, бренд-ассеты).
2. ⏸ **Юрисдикция для AI-платежей** — отложено. MVP идёт через посредников (ProxyAPI/Vsegpt). Вопрос об армянском/грузинском ИП пересматривается на год 2.
3. ✅ **Дизайнер** — не привлекаем. Дизайн-система строится на shadcn/ui + Framer Motion + Storybook силами Alex. Если упрёмся в качество — добавим контрактного дизайнера в V2.
4. 🔄 **TG-каналы для парсинга** — curated-список (30-50 каналов) собирается параллельно и кладётся в [2026-05-17-tg-channels-curated-list.md](2026-05-17-tg-channels-curated-list.md). Готов к Sprint 2.
5. ✅ **B2B-партнёрство с HH** — не подаём заявку на MVP-этапе. Используем публичное API в рамках лимитов. Партнёрство пересматривается, когда упрёмся в rate-limits или подойдёт V3 (B2B Talent Pool).

## 15a. Открытые задачи (для Sprint 1)

- Верификация домена `otklik.ai` (доступность, цена, регистрация через регистратора)
- Регистрация торговой марки «Otklik» в РФ (Роспатент) — параллельно, занимает 8-12 месяцев
- Дополнительные домены для защиты бренда: `otklik.ru`, `otklik.io`, `otklik.app` (если доступны)
- Email-домен: `team@otklik.ai`, `support@otklik.ai`
- Соцсети: `@otklik`, `@otklik_ai` на VK, Telegram, X
- Перенос существующего jobskout-репо в `otklik-ai` (GitHub rename)

---

## Следующие шаги

1. Юзер ревьюит этот документ.
2. По approve → переходим к **writing-plans** скиллу для составления детального implementation plan на Sprint 1-2.
3. План разбивается на subagent-task'и и идёт в реализацию через **subagent-driven-development** или **executing-plans**.

