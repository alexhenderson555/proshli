export interface DemoCard {
  company: string;
  title: string;
  match: number;
  tags: string[];
  salary: string;
  location: string;
}

const DEMO_CARDS: DemoCard[] = [
  {
    company: "Yandex · Platform",
    title: "Senior Backend Engineer",
    match: 94,
    tags: ["Go", "Kafka", "gRPC"],
    salary: "₽550K",
    location: "Remote",
  },
  {
    company: "Tinkoff · CoreBank",
    title: "Backend Lead",
    match: 89,
    tags: ["Go", "Postgres", "K8s"],
    salary: "₽600K",
    location: "Hybrid",
  },
  {
    company: "Avito · Search",
    title: "Search Engineer",
    match: 86,
    tags: ["Python", "Elastic", "Clickhouse"],
    salary: "₽480K",
    location: "Office",
  },
];

export async function* simulateStream(
  _query: string,
): AsyncGenerator<{ type: "text"; value: string } | { type: "card"; value: DemoCard }> {
  const intro = "Нашёл 3 вакансии по твоему запросу:";
  for (const chunk of intro.match(/.{1,4}/g) ?? []) {
    yield { type: "text", value: chunk };
    await sleep(40);
  }
  await sleep(200);
  for (const card of DEMO_CARDS) {
    yield { type: "card", value: card };
    await sleep(280);
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
