"use client";

// Lightweight Framer Motion primitives. Marketing surfaces (`apps/web`
// landing/pricing/about pages) wrap their sections in `<FadeIn>` so the
// page feels alive without each surface re-implementing the same
// entrance choreography. `<Stagger>` does the same job for a list:
// children fade in with a small delay between siblings.

import { motion } from "framer-motion";
import * as React from "react";

const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];

export interface FadeInProps {
  /** Seconds before the animation starts. */
  delay?: number;
  /** Seconds the animation takes to play. */
  duration?: number;
  /** Vertical offset (px) the element rises from. */
  y?: number;
  className?: string;
  children?: React.ReactNode;
}

export function FadeIn({
  delay = 0,
  duration = 0.45,
  y = 8,
  className,
  children,
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-10% 0px" }}
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
  className?: string;
  children?: React.ReactNode;
}

export function Stagger({
  step = 0.07,
  className,
  children,
}: StaggerProps) {
  const items = React.Children.toArray(children);
  return (
    <motion.div
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-10% 0px" }}
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
            hidden: { opacity: 0, y: 8 },
            visible: {
              opacity: 1,
              y: 0,
              transition: { duration: 0.45, ease: EASE_OUT },
            },
          }}
        >
          {child}
        </motion.div>
      ))}
    </motion.div>
  );
}
