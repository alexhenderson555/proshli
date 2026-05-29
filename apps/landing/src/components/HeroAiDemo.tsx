import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { type DemoCard, simulateStream } from "../lib/demo-stream";

const SUGGESTIONS = [
  { text: "Go Backend Belgrade", query: "Senior Go Backend в Белград от €4500" },
  { text: "Python ML Engineer", query: "ML Engineer удаленно от 400К" },
  { text: "React Frontend Moscow", query: "Frontend React/Next.js в Москву от 300К" },
];

export default function HeroAiDemo() {
  const [query, setQuery] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [phase, setPhase] = useState("");
  const [answer, setAnswer] = useState("");
  const [cards, setCards] = useState<DemoCard[]>([]);
  const [showCta, setShowCta] = useState(false);

  const startSimulation = async (searchQuery: string) => {
    if (streaming) return;
    setStreaming(true);
    setAnswer("");
    setCards([]);
    setShowCta(false);

    // Phase 1: AI Parsing Resume & Query
    setPhase("Извлечение ключевых требований из запроса...");
    await sleep(700);

    // Phase 2: Embedding projection
    setPhase("Расчёт 1024-мерного вектора (Embedding)...");
    await sleep(600);

    // Phase 3: Cosine Similarity Matching
    setPhase("Семантический поиск и скоринг по 12 847 вакансиям...");
    await sleep(800);

    setPhase("");

    for await (const frame of simulateStream(searchQuery)) {
      if (frame.type === "text") {
        setAnswer((prev) => prev + frame.value);
      } else {
        setCards((prev) => [...prev, frame.value]);
      }
    }
    setStreaming(false);
    setShowCta(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    startSimulation(query);
  };

  const handleSuggestionClick = (q: string) => {
    setQuery(q);
    startSimulation(q);
  };

  return (
    <div className="w-full bg-[#0a0a0c]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-[0_0_50px_rgba(124,58,237,0.08)] relative overflow-hidden group">
      {/* Decorative backdrop mesh */}
      <div className="absolute top-0 right-0 w-48 h-48 rounded-full bg-landing-accent-start/5 blur-[80px] pointer-events-none group-hover:bg-landing-accent-start/8 transition-colors duration-500" />
      <div className="absolute bottom-0 left-0 w-48 h-48 rounded-full bg-indigo-500/5 blur-[80px] pointer-events-none group-hover:bg-indigo-500/8 transition-colors duration-500" />

      {/* Terminal header */}
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/30" />
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/30" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/30" />
          </div>
          <span className="text-11 font-mono text-white/30 tracking-wider uppercase ml-1">proshli_query_helper.sh</span>
        </div>
        <span className="text-11 font-mono text-landing-accent-start/80 bg-landing-accent-start/10 border border-landing-accent-start/20 px-2 py-0.5 rounded">
          AI active
        </span>
      </div>

      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center">
          <svg className="absolute left-4 w-4 h-4 text-white/30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Backend в Белград от €4500..."
            disabled={streaming}
            className="w-full h-12 pl-11 pr-24 rounded-xl bg-white/[0.02] border border-white/10 text-13 text-white placeholder:text-white/20 focus:outline-none focus:border-landing-accent-start/50 focus:bg-white/[0.04] focus:shadow-[0_0_20px_rgba(124,58,237,0.15)] transition-all duration-300"
          />
          <button
            type="submit"
            disabled={streaming || !query.trim()}
            className="absolute right-1.5 top-1.5 h-9 px-5 rounded-lg bg-gradient-to-r from-landing-accent-start to-landing-accent-end text-12 font-medium text-white shadow-glow hover:opacity-90 active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed disabled:scale-100 transition-all duration-200"
          >
            {streaming ? "Поиск..." : "Найти"}
          </button>
        </div>
      </form>

      {/* Suggestions block */}
      {!streaming && cards.length === 0 && (
        <div className="mt-4">
          <div className="text-11 font-mono text-white/30 mb-2 uppercase tracking-wider">Быстрый запуск:</div>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button
                key={s.text}
                type="button"
                onClick={() => handleSuggestionClick(s.query)}
                className="text-11 font-mono px-3 py-1.5 rounded-lg border border-white/[0.05] bg-white/[0.01] text-white/50 hover:text-white hover:border-landing-accent-start/40 hover:bg-landing-accent-start/[0.04] active:scale-95 transition-all duration-200"
              >
                {s.text}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Interactive processing phases */}
      <AnimatePresence>
        {streaming && phase && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-5 border border-white/[0.05] bg-white/[0.01] rounded-xl p-4 overflow-hidden"
          >
            <div className="flex items-center gap-3">
              <span className="relative flex h-2 w-2 shrink-0">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-landing-accent-start opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-landing-accent-start"></span>
              </span>
              <span className="text-12 font-mono text-white/60">{phase}</span>
            </div>
            {/* Fake progress line */}
            <div className="w-full h-1 bg-white/[0.05] rounded-full overflow-hidden mt-3">
              <div className="h-full bg-gradient-to-r from-landing-accent-start to-landing-accent-end animate-[shimmer_1.5s_infinite_linear]" style={{ width: "100%", backgroundSize: "200% 100%" }} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Simulated stream output sentence */}
      <AnimatePresence>
        {answer && (
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 text-13 font-medium text-white/80 border-l-2 border-landing-accent-start pl-3"
          >
            {answer}
            {streaming && !phase && (
              <span className="inline-block w-1.5 h-3.5 ml-1 bg-landing-accent-start animate-[pulse_1s_infinite] rounded-sm align-middle" />
            )}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Vacancies matches grid */}
      <div className="mt-4 space-y-3">
        <AnimatePresence>
          {cards.map((card, i) => (
            <motion.div
              key={`${card.company}-${i}`}
              initial={{ opacity: 0, y: 16, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className="rounded-xl border border-white/[0.05] bg-gradient-to-r from-white/[0.01] to-transparent p-4 hover:border-landing-accent-start/35 hover:bg-white/[0.02] hover:shadow-[0_0_20px_rgba(124,58,237,0.04)] transition-all duration-300"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-11 font-mono text-white/40">{card.company}</span>
                    <span className="w-1 h-1 rounded-full bg-white/20" />
                    <span className="text-11 font-mono text-white/40">{card.location}</span>
                  </div>
                  <h4 className="text-14 font-semibold text-white mt-1 leading-snug">{card.title}</h4>
                  <div className="text-12 font-semibold text-white/80 mt-1.5">{card.salary}</div>
                </div>

                {/* Match indicator circle/box */}
                <div className="shrink-0 flex flex-col items-center">
                  <div className="px-2.5 py-1 rounded-lg border border-emerald-500/20 bg-emerald-500/10 text-emerald-400 font-mono text-12 font-bold shadow-[0_0_15px_rgba(16,185,129,0.1)]">
                    {card.match}% match
                  </div>
                </div>
              </div>

              <div className="flex gap-1.5 mt-3.5 flex-wrap">
                {card.tags.map((t) => (
                  <span
                    key={t}
                    className="text-10 font-mono px-2 py-0.5 rounded border border-white/[0.06] bg-white/[0.02] text-white/50"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* CTA overlay button */}
      <AnimatePresence>
        {showCta && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mt-6 border-t border-white/[0.06] pt-5 flex items-center justify-between gap-4 flex-wrap"
          >
            <span className="text-12 text-white/50">Хочешь получать такие вакансии каждое утро?</span>
            <a
              href="https://app.proshli.ru/auth/register"
              className="inline-flex items-center gap-1.5 text-12 font-semibold text-landing-accent-start hover:text-landing-accent-end hover:underline transition-colors"
            >
              Зарегистрируйся бесплатно
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
