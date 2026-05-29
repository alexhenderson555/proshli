/**
 * Декоративный backdrop для hero-секции.
 * Premium radial glow, floating blurred orbs, and active grid mask.
 */
export default function HeroBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      {/* Background base */}
      <div className="absolute inset-0 bg-[#070708]" />

      {/* Floating radial mesh glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,rgba(124,58,237,0.15)_0%,transparent_70%)] blur-2xl" />
      <div className="absolute top-[20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.08)_0%,transparent_60%)] blur-3xl" />
      <div className="absolute bottom-[-10%] left-[20%] w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,rgba(168,85,247,0.05)_0%,transparent_70%)] blur-2xl" />

      {/* Animated Floating Orbs */}
      <div className="absolute top-[20%] left-[15%] w-80 h-80 rounded-full bg-violet-600/[0.04] blur-3xl animate-[pulse_10s_infinite]" />
      <div className="absolute bottom-[30%] right-[10%] w-[450px] h-[450px] rounded-full bg-indigo-500/[0.03] blur-3xl animate-[pulse_15s_infinite_2s]" />

      {/* Premium grid overlay with mask fade */}
      <div className="absolute inset-0 opacity-[0.25]" style={{ maskImage: "linear-gradient(to bottom, black, transparent)" }}>
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="hero-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="rgba(255,255,255,0.03)"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-grid)" />
        </svg>
      </div>

      {/* Bottom overlay to match dark page transitions */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-[#070708] to-transparent" />
    </div>
  );
}
