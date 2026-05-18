// Surface primitive. Flat by default (`.panel`), elevated on opt-in.
//
// Linear-style cards are hairline-bordered rectangles on the page canvas.
// No shadows on the default variant — shadows imply "floating", which we
// reserve for menus and modals. `variant="elevated"` is for elements that
// genuinely need to lift off the canvas (popovers, drawer panels).

import type { ElementType, ReactNode } from "react";

import { cn } from "../lib/utils";

export interface CardProps {
  children: ReactNode;
  className?: string;
  /** `flat` (default) sits on the canvas with a hairline border. `elevated`
   *  uses the higher surface token and a subtle shadow for floating UI. */
  variant?: "flat" | "elevated";
  /** Override the rendered tag — useful for `<article>` in news / vacancy
   *  contexts so the semantic role matches the visual one. */
  as?: ElementType;
}

export function Card({
  children,
  className,
  variant = "flat",
  as: Tag = "section",
}: CardProps) {
  return (
    <Tag
      className={cn(
        variant === "elevated" ? "panel-elevated p-4" : "panel p-4",
        className,
      )}
    >
      {children}
    </Tag>
  );
}
