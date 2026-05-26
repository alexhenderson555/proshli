/**
 * Декоративный backdrop для hero-секции.
 * Radial glow + тонкая grid-сетка. Без Spline (экономим 200KB+).
 * Если нужно больше wow — заменить на Spline/r3f в отдельном PR.
 */
export default function HeroBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {/* Фиолетовый radial glow — смещён влево-вверх для асимметрии */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_30%_20%,rgba(124,58,237,0.15)_0%,transparent_70%)]" />
      {/* Тонкая grid-сетка */}
      <div className="absolute inset-0 opacity-20">
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="hero-grid" width="48" height="48" patternUnits="userSpaceOnUse">
              <path
                d="M 48 0 L 0 0 0 48"
                fill="none"
                stroke="rgba(255,255,255,0.04)"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-grid)" />
        </svg>
      </div>
    </div>
  );
}
