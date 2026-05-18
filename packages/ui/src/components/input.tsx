// Controlled text input. The Proshli convention is `onChange(value)` —
// callers don't need to unwrap `event.target.value` themselves — so
// the SDK shape diverges from the raw HTML element.
//
// We pass the rest of the props through so callers can still set
// `id`, `name`, `autoComplete`, `disabled` etc.

import * as React from "react";

import { cn } from "../lib/utils";

// Shared between Input / Select / Textarea so the three feel like one
// primitive. Editorial dense: 28px tall (h-8 equivalent via py-1.5),
// rounded 4px, elevated surface so fields read as "indents" of the
// canvas rather than raised cards.
export const fieldClass =
  "w-full rounded border border-border bg-elevated px-2.5 py-1.5 text-[13px] font-[510] text-text-primary placeholder:text-text-tertiary outline-none transition-[border-color,box-shadow] focus-visible:border-accent focus-visible:ring-1 focus-visible:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-40";

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
