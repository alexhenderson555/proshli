import Link from "next/link";
import { ArrowRight, Bot, Filter, Sparkles, Zap } from "lucide-react";

const features = [
  {
    icon: Sparkles,
    title: "AI-поиск под вас",
    body: "Опишите идеальную работу обычным языком — Otklik сам подберёт фильтры и найдёт подходящие вакансии.",
  },
  {
    icon: Filter,
    title: "Один поток вакансий",
    body: "Агрегируем HeadHunter, SuperJob, Хабр Карьеру, Telegram-каналы и десятки нишевых источников.",
  },
  {
    icon: Bot,
    title: "Telegram-доставка",
    body: "Подписка на дайджест — новые подходящие вакансии прилетают прямо в Telegram, без лишнего шума.",
  },
  {
    icon: Zap,
    title: "Быстрый отклик",
    body: "Сохранённые шаблоны и автозаполнение помогают отвечать на вакансии за секунды, а не минуты.",
  },
];

const metrics = [
  { value: "40+", label: "источников вакансий" },
  { value: "10×", label: "быстрее обычного поиска" },
  { value: "24/7", label: "AI работает за вас" },
];

export default function Home() {
  return (
    <div className="flex flex-col gap-16 py-8">
      {/* Hero */}
      <section className="grid gap-10 lg:grid-cols-[1.2fr_1fr] lg:items-center">
        <div className="flex flex-col gap-6">
          <span className="inline-flex w-fit items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-accent" />
            Beta · Russia-first
          </span>
          <h1 className="text-balance text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            Найдите работу мечты —{" "}
            <span className="bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--accent))] bg-clip-text text-transparent">
              пока AI ищет за вас
            </span>
            .
          </h1>
          <p className="max-w-2xl text-pretty text-base text-muted-foreground sm:text-lg">
            Otklik.ai собирает вакансии со всех ключевых площадок России и СНГ, понимает ваш
            запрос на естественном языке и доставляет лучшие предложения в Telegram.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/auth?mode=register"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
            >
              Начать бесплатно
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/vacancies"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-card px-5 py-3 text-sm font-semibold text-foreground transition hover:bg-muted"
            >
              Смотреть вакансии
            </Link>
          </div>
          <dl className="mt-4 grid max-w-md grid-cols-3 gap-6">
            {metrics.map((m) => (
              <div key={m.label} className="flex flex-col gap-1">
                <dt className="text-2xl font-extrabold tracking-tight text-foreground">{m.value}</dt>
                <dd className="text-xs text-muted-foreground">{m.label}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="panel relative overflow-hidden p-6 lg:p-8">
          <div className="absolute inset-0 -z-10 bg-gradient-to-br from-[hsl(var(--primary)/0.08)] via-transparent to-[hsl(var(--accent)/0.08)]" />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Bot className="h-4 w-4 text-accent" />
            Otklik AI
          </div>
          <div className="mt-4 flex flex-col gap-4">
            <div className="rounded-2xl bg-muted/60 px-4 py-3 text-sm text-foreground">
              Хочу удалённую работу Python-разработчиком, FastAPI, от 250к, без созвонов раньше 11.
            </div>
            <div className="ml-auto max-w-[85%] rounded-2xl bg-primary px-4 py-3 text-sm text-primary-foreground">
              Понял. Нашёл 14 вакансий: Python · FastAPI · remote · 250–400k ₽. Отправляю топ-3 в
              Telegram.
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full border border-border bg-card px-2.5 py-1 text-xs">
                Python
              </span>
              <span className="rounded-full border border-border bg-card px-2.5 py-1 text-xs">
                FastAPI
              </span>
              <span className="rounded-full border border-border bg-card px-2.5 py-1 text-xs">
                Remote
              </span>
              <span className="rounded-full border border-border bg-card px-2.5 py-1 text-xs">
                250–400k ₽
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="flex flex-col gap-8">
        <div className="flex flex-col gap-2">
          <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Один инструмент вместо десяти вкладок
          </h2>
          <p className="max-w-2xl text-muted-foreground">
            Otklik берёт на себя рутину поиска работы: агрегацию, фильтрацию, нотификации и
            быстрый отклик.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map(({ icon: Icon, title, body }) => (
            <article
              key={title}
              className="panel flex flex-col gap-3 p-5 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold">{title}</h3>
              <p className="text-sm text-muted-foreground">{body}</p>
            </article>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="panel flex flex-col items-start gap-4 p-8 sm:flex-row sm:items-center sm:justify-between sm:p-10">
        <div className="flex flex-col gap-2">
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
            Готовы найти работу быстрее?
          </h2>
          <p className="max-w-xl text-muted-foreground">
            Создайте аккаунт за 30 секунд и получите первый персональный дайджест уже сегодня.
          </p>
        </div>
        <Link
          href="/auth?mode=register"
          className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
        >
          Зарегистрироваться
          <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
