// Controlled text input. The Proshli convention is `onChange(value)` —
// callers don't need to unwrap `event.target.value` themselves — so
// the SDK shape diverges from the raw HTML element.
//
// We pass the rest of the props through so callers can still set
// `id`, `name`, `autoComplete`, `disabled` etc.

import * as React from "react";

import { cn } from "../lib/utils";

export const fieldClass =
  "w-full rounded-xl border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none transition focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-60";

export interface InputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  id?: string;
  name?: string;
  autoComplete?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
}

export function Input({
  value,
  onChange,
  placeholder = "",
  type = "text",
  className,
  ...rest
}: InputProps) {
  return (
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      type={type}
      className={cn(fieldClass, className)}
      {...rest}
    />
  );
}
