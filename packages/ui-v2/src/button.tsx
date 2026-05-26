import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "./lib/cn";

const buttonVariants = cva(
  // base: layout + reset + focus + transition
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-13 font-medium " +
    "transition-colors duration-fast ease-exit " +
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-dark-accent " +
    "disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-app-dark-accent text-white hover:bg-app-dark-accent/90",
        secondary:
          "border border-app-dark-border bg-transparent text-app-dark-text-primary hover:bg-app-dark-bg-secondary",
        ghost:
          "bg-transparent text-app-dark-text-muted hover:text-app-dark-text-primary hover:bg-app-dark-bg-secondary",
        danger: "bg-red-600 text-white hover:bg-red-700",
      },
      size: {
        sm: "h-7 px-2.5 text-12",
        md: "h-8 px-3",
        lg: "h-10 px-4 text-14",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />
    );
  },
);
Button.displayName = "Button";
