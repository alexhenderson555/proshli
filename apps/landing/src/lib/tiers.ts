export interface Tier {
  name: string;
  price: string;
  period: string;
  features: string[];
  cta: string;
  ctaHref: string;
  featured?: boolean;
}

export const tiers: Tier[] = [
  {
    name: "Free",
    price: "₽0",
    period: "навсегда",
    features: [
      "3 AI-запроса в день",
      "Дайджест раз в неделю",
      "Базовый match-score",
    ],
    cta: "Начать",
    ctaHref: "https://app.proshli.ru/auth/register",
  },
  {
    name: "Pro",
    price: "₽490",
    period: "месяц",
    features: [
      "Безлимит AI-запросов",
      "Дайджест каждый день",
      "Match-score с обоснованием",
      "AI-улучшение резюме",
    ],
    cta: "Попробовать Pro",
    ctaHref: "https://app.proshli.ru/billing?plan=pro",
    featured: true,
  },
  {
    name: "Employer",
    price: "₽4 900",
    period: "месяц",
    features: [
      "Размещение вакансий",
      "Кандидаты с AI-скринингом",
      "Команда до 5 человек",
      "Приоритетная поддержка",
    ],
    cta: "Для компаний",
    ctaHref: "https://app.proshli.ru/employer",
  },
];
