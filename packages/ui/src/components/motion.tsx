"use client";

// Lightweight Framer Motion primitives.
//
// Motion policy (Linear-style editorial dense):
//   * Duration ≤ 0.5s — anything longer reads as "loading"
//   * Translate ≤ 16px — beyond that it's distracting
//   * Stagger step ≤ 0.08s — keeps the cascade from feeling slow
//   * Respect `prefers-reduced-motion` — short-circuit to static
//
// All primitives gate on `useReducedMotion()` and render the children
// statically (no opacity ramp, no translate) when the user opts out.

import { motion, useReducedMotion } from "framer-motion";
import * as React from "react";

// Curves
export const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];
export const EASE_SHARP: [number, number, number, number] = [0.32, 0, 0.67, 0];

export interface FadeInProps {
  /** Seconds before the animation starts. */
  delay?: number;
  /** Seconds the animation takes to play. */
  duration?: number;
  /** Vertical offset (px) the element rises from. */
  y?: number;
  /** When true, animate on mount instead of `whileInView`. Use for
   *  above-the-fold content where IntersectionObserver delay would
   *  otherwise leave the hero invisible for ~50ms after first paint. */
  immediate?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function FadeIn({
  delay = 0,
  duration = 0.4,
  y = 6,
  immediate = false,
  className,
  children,
}: FadeInProps) {
  const reduced = useReducedMotion();
  if (reduced) {
    return <div className={className}>{children}</div>;
  }
  const trigger = immediate
    ? { animate: { opacity: 1, y: 0 } }
    : {
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: "-10% 0px" },
      };
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      {...trigger}
      transition={{ delay, duration, ease: EASE_OUT }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export interface FadeInDownProps extends Omit<FadeInProps, "y"> {}

/** Same as FadeIn but the element drops *into* place from above. Use for
 *  toasts, dropdown menus, header-anchored alerts. */
export function FadeInDown(props: FadeInDownProps) {
  return <FadeIn {...props} y={-6} immediate />;
}

export interface ScaleFadeProps {
  delay?: number;
  duration?: number;
  className?: string;
  children?: React.ReactNode;
}

/** Opacity + subtle scale lift. Reserved for modals / drawers / popovers
 *  where the surface arrives from a focal point rather than sliding. */
export function ScaleFade({
  delay = 0,
  duration = 0.2,
  className,
  children,
}: ScaleFadeProps) {
  const reduced = useReducedMotion();
  if (reduced) {
    return <div className={className}>{children}</div>;
  }
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.98 }}
      transition={{ delay, duration, ease: EASE_OUT }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export interface StaggerProps {
  /** Seconds between consecutive child fade-ins. */
  step?: number;
  /** When true, animate on mount instead of `whileInView`. */
  immediate?: boolean;
  /** Vertical offset (px) each child rises from. */
  y?: number;
  className?: string;
  children?: React.ReactNode;
}

export function Stagger({
  step = 0.05,
  immediate = false,
  y = 6,
  className,
  children,
}: StaggerProps) {
  const reduced = useReducedMotion();
  const items = React.Children.toArray(children);
  if (reduced) {
    return <div className={className}>{children}</div>;
  }
  const trigger = immediate
    ? { animate: "visible" as const }
    : {
        whileInView: "visible" as const,
        viewport: { once: true, margin: "-10% 0px" },
      };
  return (
    <motion.div
      initial="hidden"
      {...trigger}
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: step } },
      }}
      className={className}
    >
      {items.map((child, index) => (
        <motion.div
          key={index}
          variants={{
            hidden: { opacity: 0, y },
            visible: {
              opacity: 1,
              y: 0,
              transition: { duration: 0.35, ease: EASE_OUT },
            },
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
