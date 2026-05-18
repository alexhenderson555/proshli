// Controlled multi-line input. Same `onChange(value)` convention as
// `Input`, with an explicit `rows` default and a `min-h` so the
// textarea is usable even before content arrives.

import * as React from "react";

import { cn } from "../lib/utils";
import { fieldClass } from "./input";

export interface TextareaProps
  extends Omit<
    React.TextareaHTMLAttributes<HTMLTextAreaElement>,
    "value" | "onChange" | "rows"
  > {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  className?: string;
}

export function Textarea({
  value,
  onChange,
  placeholder = "",
  rows = 4,
  className,
  ...rest
}: TextareaProps) {
  return (
    <textarea
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      rows={rows}
      className={cn(fieldClass, "min-h-[80px] py-2 resize-y leading-[1.55]", className)}
      {...rest}
    />
  );
}
