import { useState } from "react";

export default function TimeCalculator() {
  const [minutes, setMinutes] = useState(45); // Minutes spent daily
  const [salary, setSalary] = useState(250000); // Target monthly salary

  // Calculations
  const hoursPerMonth = Math.round((minutes * 30) / 60);
  const hourlyRate = Math.round(salary / 168); // 168 working hours in a month
  const wastedMoney = hoursPerMonth * hourlyRate;

  // Benefits
  const proshliTimePerMonth = Math.round((2 * 30) / 60); // 2 mins daily
  const savedHours = hoursPerMonth - proshliTimePerMonth;
  const savedMoney = savedHours * hourlyRate;

  return (
    <div className="w-full max-w-4xl mx-auto bg-[#0a0a0c]/80 backdrop-blur-xl border border-white/10 rounded-3xl p-6 md:p-10 shadow-[0_0_50px_rgba(124,58,237,0.06)] relative overflow-hidden group">
      {/* Glow highlight */}
      <div className="absolute top-0 left-1/4 w-72 h-72 bg-landing-accent-start/5 rounded-full blur-[100px] pointer-events-none" />
      <div className="absolute bottom-0 right-1/4 w-72 h-72 bg-emerald-500/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="grid md:grid-cols-2 gap-10 items-center relative z-10">
        {/* Sliders on Left */}
        <div className="space-y-8">
          <div>
            <h3 className="text-20 font-bold text-white tracking-tight">Калькулятор потерянного времени</h3>
            <p className="text-13 text-landing-text-muted mt-1 leading-relaxed">
              Посчитайте, сколько часов вашей жизни и денег сгорает на ручной скроллинг вакансий.
            </p>
          </div>

          <div className="space-y-5">
            {/* Slider 1: Minutes */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-13 font-mono">
                <span className="text-white/60">Время на hh.ru / Хабре:</span>
                <span className="text-landing-accent-start font-bold text-14">{minutes} мин / день</span>
              </div>
              <input
                type="range"
                min="10"
                max="180"
                step="5"
                value={minutes}
                onChange={(e) => setMinutes(Number(e.target.value))}
                className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-landing-accent-start focus:outline-none"
              />
              <div className="flex justify-between text-[10px] text-white/30 font-mono">
                <span>10 мин</span>
                <span>3 часа</span>
              </div>
            </div>

            {/* Slider 2: Target Salary */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-13 font-mono">
                <span className="text-white/60">Желаемый оклад в месяц:</span>
                <span className="text-emerald-400 font-bold text-14">
                  {salary.toLocaleString("ru-RU")} ₽
                </span>
              </div>
              <input
                type="range"
                min="80000"
                max="700000"
                step="10000"
                value={salary}
                onChange={(e) => setSalary(Number(e.target.value))}
                className="w-full h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-emerald-400 focus:outline-none"
              />
              <div className="flex justify-between text-[10px] text-white/30 font-mono">
                <span>80K ₽</span>
                <span>700K ₽</span>
              </div>
            </div>
          </div>
        </div>

        {/* Real-time stats output on Right */}
        <div className="bg-black/40 border border-white/[0.06] rounded-2xl p-6 md:p-8 flex flex-col justify-between min-h-[260px] relative overflow-hidden">
          <div className="space-y-5">
            <div>
              <div className="text-11 font-mono uppercase tracking-wider text-white/30">Без Proshli AI вы тратите:</div>
              <div className="flex items-baseline gap-2 mt-1.5">
                <span className="text-36 font-bold font-mono text-white leading-none">{hoursPerMonth}</span>
                <span className="text-13 text-white/50">часов в месяц</span>
              </div>
              <p className="text-12 text-white/40 mt-1 font-mono">
                В год это ~{hoursPerMonth * 12} часов рутинного скроллинга.
              </p>
            </div>

            <div className="h-[1px] bg-white/[0.06] w-full" />

            <div>
              <div className="text-11 font-mono uppercase tracking-wider text-white/30">Стоимость вашего времени поиска:</div>
              <div className="flex items-baseline gap-2 mt-1.5">
                <span className="text-36 font-bold font-mono text-red-400 leading-none">
                  {wastedMoney.toLocaleString("ru-RU")} ₽
                </span>
                <span className="text-13 text-red-400/80">/ мес</span>
              </div>
              <p className="text-12 text-white/40 mt-1 font-mono">
                Исходя из вашей ставки в {hourlyRate} ₽ / час.
              </p>
            </div>
          </div>

          <div className="mt-6 pt-5 border-t border-white/[0.06] flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="text-11 font-mono uppercase text-emerald-400 font-semibold tracking-wider">Выгода с Proshli:</div>
              <div className="text-14 font-bold text-white mt-0.5">
                +{savedHours} часов и {savedMoney.toLocaleString("ru-RU")} ₽
              </div>
            </div>
            <a
              href="https://app.proshli.ru/auth/register"
              className="text-12 font-bold text-white bg-landing-accent-start hover:opacity-95 px-4 h-9 inline-flex items-center rounded-lg shadow-glow active:scale-[0.98] transition-all duration-200"
            >
              Забрать выгоду
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
