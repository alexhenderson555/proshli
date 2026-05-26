import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";

import { type DemoCard, simulateStream } from "../lib/demo-stream";

export default function HeroAiDemo() {
  const [query, setQuery] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [answer, setAnswer] = useState("");
  const [cards, setCards] = useState<DemoCard[]>([]);
  const [showCta, setShowCta] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || streaming) return;
    setStreaming(true);
    setAnswer("");
    setCards([]);
    setShowCta(false);
    for await (const frame of simulateStream(query)) {
      if (frame.type === "text") setAnswer((prev) => prev + frame.value);
      else setCards((prev) => [...prev, frame.value]);
    }
    setStreaming(false);
    setShowCta(true);
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Backend в Москву от 400К"
          disabled={streaming}
          className="w-full h-12 px-4 pr-28 rounded-lg bg-white/5 border border-white/10 text-14 text-white placeholder:text-white/30 focus:outline-none focus:border-landing-accent-start/60 focus:shadow-glow transition-all"
        />
        <button
          type="submit"
          disabled={streaming || !query.trim()}
          className="absolute right-1.5 top-1.5 h-9 px-4 rounded-md bg-gradient-to-r from-landing-accent-start to-landing-accent-end text-12 font-medium text-white disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {streaming ? "Ищу..." : "Найти"}
        </button>
      </form>

      <AnimatePresence>
        {answer && (
          <motion.p
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-5 text-13 text-white/70"
          >
            {answer}
            {streaming && (
              <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-landing-accent-start animate-pulse rounded-sm" />
            )}
          </motion.p>
        )}
      </AnimatePresence>

      <div className="mt-3 space-y-2.5">
        <AnimatePresence>
          {cards.map((card, i) => (
            <motion.div
              key={`${card.company}-${i}`}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="rounded-lg border border-white/8 bg-white/[0.03] p-4 backdrop-blur-sm hover:border-landing-accent-start/30 transition-colors cursor-pointer"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-14 font-semibold text-white">{card.title}</div>
                  <div className="text-12 text-white/50 mt-0.5">
                    {card.company} · {card.location} · {card.salary}
                  </div>
                </div>
                <span className="shrink-0 text-12 font-mono font-medium text-landing-accent-start">
                  {card.match}%
                </span>
              </div>
              <div className="flex gap-1.5 mt-2.5 flex-wrap">
                {card.tags.map((t) => (
                  <span
                    key={t}
                    className="text-11 px-2 py-0.5 rounded-full border border-white/8 text-white/60"
                  >
                    {t}
                  </span>
                ))}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {showCta && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-5"
          >
            <a
              href="https://app.proshli.ru/auth/register"
              className="inline-flex items-center gap-1.5 text-13 text-landing-accent-start hover:text-landing-accent-end transition-colors"
            >
              Зарегистрируйся, чтобы получать такие матчи каждый день
              <span aria-hidden="true">&rarr;</span>
            </a>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
