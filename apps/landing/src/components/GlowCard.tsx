import { useRef, useState } from "react";

interface GlowCardProps {
  children: React.ReactNode;
  className?: string;
}

export default function GlowCard({ children, className = "" }: GlowCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const [rotation, setRotation] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current;
    if (!card) return;

    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left; // Mouse x relative to card
    const y = e.clientY - rect.top;  // Mouse y relative to card
    
    // Calculate tilt angles (max 8 degrees tilt)
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((centerY - y) / centerY) * 6;
    const rotateY = ((x - centerX) / centerX) * 6;

    setCoords({ x, y });
    setRotation({ x: rotateX, y: rotateY });
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setRotation({ x: 0, y: 0 });
  };

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      className={`relative rounded-3xl border border-white/[0.06] bg-gradient-to-b from-white/[0.02] to-transparent overflow-hidden transition-all duration-300 ${className}`}
      style={{
        transform: isHovered
          ? `perspective(1000px) rotateX(${rotation.x}deg) rotateY(${rotation.y}deg) scale3d(1.01, 1.01, 1.01)`
          : "perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)",
        boxShadow: isHovered
          ? "0 20px 40px rgba(0, 0, 0, 0.4), 0 0 30px rgba(124, 58, 237, 0.05)"
          : "0 4px 20px rgba(0, 0, 0, 0.2)",
      }}
    >
      {/* Interactive Spotlight Glow layer */}
      {isHovered && (
        <div
          className="pointer-events-none absolute -inset-px rounded-3xl transition-opacity duration-300 opacity-100"
          style={{
            background: `radial-gradient(400px circle at ${coords.x}px ${coords.y}px, rgba(124, 58, 237, 0.08), transparent 85%)`,
          }}
        />
      )}
      
      {/* Subtle border highlight following cursor */}
      {isHovered && (
        <div
          className="pointer-events-none absolute -inset-px rounded-3xl opacity-100"
          style={{
            background: `radial-gradient(150px circle at ${coords.x}px ${coords.y}px, rgba(255, 255, 255, 0.12), transparent 80%)`,
            maskImage: "linear-gradient(black, black)",
            WebkitMaskImage: "linear-gradient(black, black)",
          }}
        />
      )}

      <div className="relative z-10 h-full flex flex-col justify-between">
        {children}
      </div>
    </div>
  );
}
