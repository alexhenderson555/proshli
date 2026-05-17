import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-24 text-center">
      <span className="font-mono text-6xl font-extrabold text-muted-foreground">404</span>
      <h1 className="text-balance text-3xl font-extrabold tracking-tight sm:text-4xl">
        Страница не найдена
      </h1>
      <p className="max-w-md text-sm text-muted-foreground">
        Возможно, она переехала или ссылка устарела. Загляните на главную или в каталог вакансий.
      </p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
        >
          <ArrowLeft className="h-4 w-4" />
          На главную
        </Link>
        <Link
          href="/vacancies"
          className="rounded-xl border border-border bg-card px-4 py-2 text-sm font-semibold text-foreground transition hover:bg-muted"
        >
          К вакансиям
        </Link>
      </div>
    </div>
  );
}
