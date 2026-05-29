"use client";

export function HeroBackdrop() {
  return (
    <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <style>{`
        @keyframes orb-float-1 {
          0%, 100% { transform: translate(0px, 0px) scale(1); }
          50% { transform: translate(15px, -25px) scale(1.05); }
        }
        @keyframes orb-float-2 {
          0%, 100% { transform: translate(0px, 0px) scale(1); }
          50% { transform: translate(-20px, 20px) scale(0.98); }
        }
        .animate-orb-1 {
          animation: orb-float-1 14s ease-in-out infinite;
        }
        .animate-orb-2 {
          animation: orb-float-2 20s ease-in-out infinite;
        }
      `}</style>

      {/* Background base */}
      <div className="absolute inset-0 bg-[#070708]" />

      {/* Floating radial mesh glows */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.12)_0%,transparent_70%)] blur-2xl" />
      <div className="absolute top-[20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.08)_0%,transparent_60%)] blur-3xl" />
      <div className="absolute bottom-[-10%] left-[20%] w-[50%] h-[50%] rounded-full bg-[radial-gradient(circle,rgba(99,102,241,0.04)_0%,transparent_70%)] blur-2xl" />

      {/* Animated Floating Orbs */}
      <div className="absolute top-[15%] left-[10%] w-80 h-80 rounded-full bg-indigo-600/[0.03] blur-3xl animate-orb-1" />
      <div className="absolute bottom-[20%] right-[5%] w-[450px] h-[450px] rounded-full bg-indigo-500/[0.02] blur-3xl animate-orb-2" />

      {/* Premium grid overlay with mask fade */}
      <div className="absolute inset-0 opacity-[0.3]" style={{ maskImage: "linear-gradient(to bottom, black, transparent)" }}>
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="hero-grid-next" width="40" height="40" patternUnits="userSpaceOnUse">
              <path
                d="M 40 0 L 0 0 0 40"
                fill="none"
                stroke="rgba(255,255,255,0.03)"
                strokeWidth="1"
              />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-grid-next)" />
        </svg>
      </div>

      {/* Bottom overlay to match dark page transitions */}
      <div className="absolute bottom-0 left-0 right-0 h-40 bg-gradient-to-t from-[#070708] to-transparent" />
    </div>
  );
}
