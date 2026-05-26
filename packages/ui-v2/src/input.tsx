import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "./lib/cn";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, type = "text", ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          "flex h-8 w-full rounded-md border border-app-dark-border bg-app-dark-bg-secondary px-3 text-13 text-app-dark-text-primary",
          "placeholder:text-app-dark-text-subtle",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-app-dark-accent focus-visible:ring-offset-0",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-red-500 focus-visible:ring-red-500",
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";
