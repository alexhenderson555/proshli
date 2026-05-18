// Controlled `<select>` matching the Otklik `onChange(value)` shape.
// Options are passed as `{value, label}` so the call site doesn't have
// to declare a child JSX list. The `appearance-none` strips browser
// chrome so the field visually aligns with `Input` / `Textarea`.

import { cn } from "../lib/utils";
import { fieldClass } from "./input";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  className?: string;
}

export function Select({ value, onChange, options, className }: SelectProps) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className={cn(fieldClass, "appearance-none pr-8", className)}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
