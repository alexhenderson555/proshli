// Linear-style Button. Compact, low-radius, color-shift hover (no lift).
//
// Variants: primary (filled accent), secondary (elevated chip with border),
// ghost (transparent), danger. Sizes are tight — md is 32px tall, the
// editorial-density default. Use `lg` only when the button is the page's
// dominant CTA (auth submit, billing plan select).
//
// Focus ring is built into the base class — `ring-accent` shows on
// keyboard nav only (`focus-visible`), never on mouse click.

import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "../lib/utils";

const buttonVariants = cva(
  // Base: rounded (4px), inter 510, no shadow, color-only transitions.
  "inline-flex items-center justify-center gap-1.5 rounded font-[510] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-canvas disabled:cursor-not-allowed disabled:opacity-40 select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-white hover:bg-accent-hover active:bg-accent-active",
        secondary:
          "bg-elevated text-text-primary border border-border hover:border-border-strong hover:bg-elevated",
        ghost:
          "bg-transparent text-text-secondary hover:bg-elevated hover:text-text-primary",
        danger:
          "bg-danger text-white hover:opacity-90 active:opacity-95",
      },
      size: {
        sm: "h-7 px-2.5 text-[12px]",
        md: "h-8 px-3 text-[13px]",
        lg: "h-9 px-4 text-[14px]",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, type = "button", ...props }, ref) => (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  ),
);
Button.displayName = "Button";

export { buttonVariants };
