# JobSkout Web (Next.js)

## Что делает продукт

Основной **веб-интерфейс** монорепозитория JobSkout: вакансии, профили, сценарии соискателя/работодателя. Собран на **Next.js** (см. также корневой `README.md` проекта).

## Преимущества

- App Router, быстрый dev-цикл, общий API с бэкендом FastAPI.

## Установка

```bash
cd web
npm install
```

Создайте окружение (минимум):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Запуск:

```bash
npm run dev
```

Откройте [http://localhost:3000](http://localhost:3000) (типичный путь к вакансиям: `/vacancies` — см. корневой README).

Дополнительно: `npm run lint`, `npm run build`, `npm run test:e2e`.

## Траблшутинг

| Проблема | Что проверить |
|----------|----------------|
| Нет данных /404 на API | Запущен ли бэкенд, верный ли `NEXT_PUBLIC_API_URL`. |
| CORS / сетевые ошибки | URL схема http/https, файрвол. |
| Сборка падает | Версия Node, `npm ci` vs `npm install`, логи `npm run build`. |

Шаблон create-next-app и документация Next.js: [nextjs.org/docs](https://nextjs.org/docs).
