import type { ReactNode } from "react";

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  className?: string;
};

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled = false,
  className = "",
}: ButtonProps) {
  const variantClass =
    variant === "primary"
      ? "bg-[var(--brand)] text-white hover:bg-[var(--brand-strong)]"
      : variant === "secondary"
        ? "bg-white text-[var(--text)] border border-[var(--line)] hover:bg-[var(--surface-alt)]"
        : variant === "danger"
          ? "bg-[var(--danger)] text-white hover:opacity-90"
          : "bg-transparent text-[var(--brand)] hover:bg-[var(--surface-alt)]";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${variantClass} disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    >
      {children}
    </button>
  );
}

type InputProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
};

export function Input({ value, onChange, placeholder = "", type = "text" }: InputProps) {
  return (
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      type={type}
      className="w-full rounded-xl border border-[var(--line)] bg-white px-3 py-2 text-sm outline-none transition focus:border-[var(--brand)]"
    />
  );
}

type TextareaProps = {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
};

export function Textarea({ value, onChange, placeholder = "", rows = 4 }: TextareaProps) {
  return (
    <textarea
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      rows={rows}
      className="w-full rounded-xl border border-[var(--line)] bg-white px-3 py-2 text-sm outline-none transition focus:border-[var(--brand)]"
    />
  );
}

type SelectProps = {
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
};

export function Select({ value, onChange, options }: SelectProps) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full rounded-xl border border-[var(--line)] bg-white px-3 py-2 text-sm outline-none transition focus:border-[var(--brand)]"
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`panel p-4 ${className}`}>{children}</section>;
}

export function Badge({
  text,
  tone = "neutral",
}: {
  text: string;
  tone?: "neutral" | "brand" | "success" | "warning";
}) {
  const toneClass =
    tone === "brand"
      ? "bg-blue-100 text-blue-700"
      : tone === "success"
        ? "bg-emerald-100 text-emerald-700"
        : tone === "warning"
          ? "bg-amber-100 text-amber-700"
          : "bg-slate-100 text-slate-700";
  return <span className={`rounded-full px-2 py-1 text-xs font-semibold ${toneClass}`}>{text}</span>;
}
