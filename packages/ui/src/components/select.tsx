// Controlled `<select>` matching the Proshli `onChange(value)` shape.
//
// `appearance-none` strips the browser chevron so we can paint our own
// SVG arrow via the inlined background-image data URI. The chevron sits
// at the right edge using `background-position` so it lines up with the
// `pr-8` reserved space regardless of field width.

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

// Hand-rolled chevron — Inter-style geometric strokes, color via stroke
// inheritance. We use rgba(231,233,238,0.5) directly (matching
// --text-secondary at ~0.5) since CSS variables can't be embedded in
// data URIs reliably across browsers.
const chevronBg =
  "bg-no-repeat bg-[length:14px_14px] bg-[position:right_8px_center] bg-[url('data:image/svg+xml;utf8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20viewBox%3D%220%200%2014%2014%22%20fill%3D%22none%22%20stroke%3D%22rgba(231%2C233%2C238%2C0.5)%22%20stroke-width%3D%221.5%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%223.5%2C5.5%207%2C9%2010.5%2C5.5%22%2F%3E%3C%2Fsvg%3E')]";

export function Select({ value, onChange, options, className }: SelectProps) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className={cn(fieldClass, "appearance-none pr-7", chevronBg, className)}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
