import { useEffect, useRef } from "react";

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  baseRadius: number;
  color: string;
  glowColor: string;
  alpha: number;
  pulseSpeed: number;
  pulsePhase: number;
}

export default function InteractiveSpace() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -1000, y: -1000, active: false });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Generate nodes representing "semantic vacancies" in space
    const nodes: Node[] = [];
    const nodeCount = Math.min(85, Math.floor((width * height) / 18000));

    const colors = [
      { base: "rgba(124, 58, 237,", glow: "rgba(168, 85, 247, 0.4)" }, // Purple
      { base: "rgba(99, 102, 241,", glow: "rgba(129, 140, 248, 0.3)" }, // Indigo
      { base: "rgba(16, 185, 129,", glow: "rgba(52, 211, 153, 0.3)" },  // Emerald (matches)
    ];

    for (let i = 0; i < nodeCount; i++) {
      const colorScheme = colors[Math.floor(Math.random() * colors.length)];
      const baseRadius = 1.5 + Math.random() * 2;
      nodes.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        radius: baseRadius,
        baseRadius,
        color: colorScheme.base,
        glowColor: colorScheme.glow,
        alpha: 0.15 + Math.random() * 0.45,
        pulseSpeed: 0.02 + Math.random() * 0.03,
        pulsePhase: Math.random() * Math.PI * 2,
      });
    }

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
      mouseRef.current.active = true;
    };

    const handleMouseLeave = () => {
      mouseRef.current.active = false;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);

    // Laser sweeps line variables
    let sweepY = 0;
    const sweepSpeed = 0.8;

    const draw = () => {
      ctx.clearRect(0, 0, width, height);

      // 1. Render deep space grid
      ctx.strokeStyle = "rgba(255, 255, 255, 0.015)";
      ctx.lineWidth = 1;
      const gridSize = 50;

      for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // 2. Render background scanning sweep
      sweepY = (sweepY + sweepSpeed) % height;
      const gradient = ctx.createLinearGradient(0, sweepY - 120, 0, sweepY);
      gradient.addColorStop(0, "rgba(124, 58, 237, 0)");
      gradient.addColorStop(0.5, "rgba(124, 58, 237, 0.025)");
      gradient.addColorStop(1, "rgba(124, 58, 237, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, sweepY - 120, width, 120);

      // 3. Draw connection lines between near nodes (Neural net)
      for (let i = 0; i < nodes.length; i++) {
        const nodeA = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const nodeB = nodes[j];
          const dx = nodeA.x - nodeB.x;
          const dy = nodeA.y - nodeB.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 110) {
            const alpha = (1 - dist / 110) * 0.08;
            ctx.strokeStyle = `rgba(124, 58, 237, ${alpha})`;
            ctx.lineWidth = 0.75;
            ctx.beginPath();
            ctx.moveTo(nodeA.x, nodeA.y);
            ctx.lineTo(nodeB.x, nodeB.y);
            ctx.stroke();
          }
        }
      }

      // 4. Update and draw nodes
      const mouse = mouseRef.current;
      for (let i = 0; i < nodes.length; i++) {
        const node = nodes[i];

        // Apply slight orbital motion
        node.x += node.vx;
        node.y += node.vy;

        // Bounce off walls
        if (node.x < 0 || node.x > width) node.vx *= -1;
        if (node.y < 0 || node.y > height) node.vy *= -1;

        // Keep inside bounds
        node.x = Math.max(0, Math.min(width, node.x));
        node.y = Math.max(0, Math.min(height, node.y));

        // Interaction with mouse pointer (magnetic pull)
        if (mouse.active) {
          const dx = mouse.x - node.x;
          const dy = mouse.y - node.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 220) {
            const force = (1 - dist / 220) * 0.15;
            node.x += (dx / dist) * force;
            node.y += (dy / dist) * force;

            // Draw a subtle halo connection from mouse to nearby nodes
            if (dist < 140) {
              const rayAlpha = (1 - dist / 140) * 0.04;
              ctx.strokeStyle = `rgba(255, 255, 255, ${rayAlpha})`;
              ctx.lineWidth = 0.5;
              ctx.beginPath();
              ctx.moveTo(mouse.x, mouse.y);
              ctx.lineTo(node.x, node.y);
              ctx.stroke();
            }
          }
        }

        // Handle pulsing node radii
        node.pulsePhase += node.pulseSpeed;
        const currentRadius = node.baseRadius + Math.sin(node.pulsePhase) * 0.5;

        // Draw glowing aura around the node
        ctx.shadowColor = node.glowColor;
        ctx.shadowBlur = 8;

        ctx.fillStyle = `${node.color}${node.alpha})`;
        ctx.beginPath();
        ctx.arc(node.x, node.y, currentRadius, 0, Math.PI * 2);
        ctx.fill();

        // Draw center solid core
        ctx.shadowBlur = 0;
        ctx.fillStyle = `rgba(255, 255, 255, ${node.alpha + 0.25})`;
        ctx.beginPath();
        ctx.arc(node.x, node.y, currentRadius * 0.45, 0, Math.PI * 2);
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none -z-10 bg-[#030304]"
      style={{ mixBlendMode: "screen" }}
    />
  );
}
