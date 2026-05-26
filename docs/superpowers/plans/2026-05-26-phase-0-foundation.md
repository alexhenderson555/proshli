# Phase 0: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Подготовить foundation для frontend-рерайта (новые packages `design-tokens` + `ui-v2`), закрыть quick-win баг с AI-гейтом (английские IT-запросы режутся), и обновить Caddy для будущего host-routing на `app.proshli.ru`. Пользовательский видимый эффект на этой фазе — только фикс AI guardrails (английские роли начинают работать).

**Architecture:** Создаём 2 новых workspace package, которые пока никем не потребляются — shared foundation для Phase 1 (Astro landing) и Phase 2 (Next.js app shell). Параллельно правим `apps/api/app/services/ai_guardrails.py` и расширяем Caddy. Все изменения изолированы — не ломают существующий прод.

**Tech Stack:** TypeScript 5, Tailwind v4, Radix UI primitives, custom build script (без Style Dictionary — overkill для нашего размера), Python 3.12, pytest, Caddy 2.x.

**Working directory:** `C:/Users/Alex/Cursor/jobskout/`

**Reference spec:** `docs/superpowers/specs/2026-05-26-frontend-million-design.md`

---

## File Structure

**New files:**

```
packages/
├── design-tokens/
│   ├── package.json
│   ├── tsconfig.json
│   ├── .gitignore
│   ├── tokens.json          ← single source of truth
│   ├── build.ts             ← компилирует JSON в CSS / TS / Tailwind preset
│   └── src/
│       └── index.ts         ← re-exports (typed access)
├── ui-v2/
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.build.json
│   ├── tailwind.config.ts   ← extends preset из design-tokens
│   └── src/
│       ├── index.ts
│       ├── button.tsx       + button.test.tsx
│       ├── input.tsx        + input.test.tsx
│       ├── dialog.tsx       + dialog.test.tsx
│       ├── sheet.tsx        + sheet.test.tsx
│       ├── tooltip.tsx      + tooltip.test.tsx
│       └── lib/
│           └── cn.ts        ← clsx + tailwind-merge helper
```

**Modified files:**
- `apps/api/app/services/ai_guardrails.py` — расширяем `CAREER_KEYWORDS`
- `apps/api/tests/test_ai_guardrails.py` — новые тесты (или создаём, если нет)
- `deploy/Caddyfile` — добавляем `app.proshli.ru` блок (пока проксирует на тот же web до Phase 2)
- `pnpm-workspace.yaml` — без изменений (уже globs `packages/*`)

**Out of scope этой фазы:** DNS-запись для `app.proshli.ru` (делает оператор вручную после деплоя), деплой Caddy в прод (отложен до Phase 1, когда `proshli.ru` начнёт указывать на Astro).

---

## Task 1: `packages/design-tokens` — JSON-схема и build script

**Files:**
- Create: `packages/design-tokens/package.json`
- Create: `packages/design-tokens/tsconfig.json`
- Create: `packages/design-tokens/.gitignore`
- Create: `packages/design-tokens/tokens.json`
- Create: `packages/design-tokens/build.ts`
- Create: `packages/design-tokens/src/index.ts`

- [ ] **Step 1: Создать package skeleton**

Создать `packages/design-tokens/package.json`:

```json
{
  "name": "@proshli/design-tokens",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts",
    "./tokens.json": "./tokens.json",
    "./tokens.css": "./dist/tokens.css",
    "./tailwind": "./dist/tailwind.cjs"
  },
  "scripts": {
    "build": "tsx build.ts",
    "lint": "eslint src",
    "type-check": "tsc --noEmit"
  },
  "devDependencies": {
    "tsx": "^4.19.0",
    "typescript": "^5.6.0",
    "@proshli/tsconfig": "workspace:*"
  }
}
```

Создать `packages/design-tokens/tsconfig.json`:

```json
{
  "extends": "@proshli/tsconfig/library.json",
  "include": ["src", "build.ts", "tokens.json"],
  "exclude": ["dist", "node_modules"]
}
```

Создать `packages/design-tokens/.gitignore`:

```
dist/
node_modules/
*.tsbuildinfo
```

- [ ] **Step 2: Написать tokens.json**

Создать `packages/design-tokens/tokens.json`. Значения — см. секцию «Design System» в `docs/superpowers/specs/2026-05-26-frontend-million-design.md:165-217`. Структура:

```json
{
  "color": {
    "landing": {
      "bg": { "primary": "#0a0a0a", "secondary": "#1a0b2e" },
      "accent": { "start": "#7c3aed", "end": "#a855f7" },
      "text": { "primary": "#ffffff", "muted": "rgba(255,255,255,0.6)" },
      "glow": "rgba(124,58,237,0.35)"
    },
    "app": {
      "dark": {
        "bg": { "primary": "#0a0a0b", "secondary": "#19191c", "tertiary": "#2a2a30" },
        "border": "#1c1c22",
        "accent": "#5e6ad2",
        "text": { "primary": "#e6e6e9", "muted": "#9a9aa3", "subtle": "#7a7a82" }
      },
      "light": {
        "bg": { "primary": "#f7f7f8", "secondary": "#ffffff" },
        "border": "#e4e4e7",
        "accent": "#5e6ad2",
        "text": { "primary": "#18181b", "muted": "#71717a" }
      }
    }
  },
  "spacing": {
    "1": "4px", "2": "8px", "3": "12px", "4": "16px",
    "6": "24px", "8": "32px", "10": "40px", "12": "48px",
    "16": "64px", "20": "80px", "24": "96px"
  },
  "radius": {
    "sm": "4px", "md": "6px", "lg": "8px", "xl": "12px", "2xl": "16px", "full": "9999px"
  },
  "font": {
    "family": {
      "sans": "'Inter Variable', system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
      "mono": "'JetBrains Mono Variable', ui-monospace, monospace"
    },
    "size": {
      "11": "11px", "12": "12px", "13": "13px", "14": "14px", "16": "16px",
      "18": "18px", "20": "20px", "24": "24px", "32": "32px", "48": "48px", "72": "72px"
    },
    "weight": { "regular": 400, "medium": 500, "semibold": 600, "bold": 700, "extrabold": 800 },
    "leading": { "tight": 1.1, "normal": 1.5, "loose": 1.75 },
    "tracking": { "tight": "-0.03em", "snug": "-0.02em", "normal": "0", "wide": "0.06em", "wider": "0.18em" }
  },
  "motion": {
    "duration": { "instant": "100ms", "fast": "150ms", "normal": "250ms", "slow": "400ms", "lazy": "600ms" },
    "easing": { "exit": "cubic-bezier(0.16, 1, 0.3, 1)", "linear": "linear", "in-out": "ease-in-out" }
  },
  "shadow": {
    "xs": "0 1px 2px rgba(0,0,0,0.05)",
    "sm": "0 2px 8px rgba(0,0,0,0.08)",
    "md": "0 4px 16px rgba(0,0,0,0.12)",
    "lg": "0 12px 32px rgba(0,0,0,0.18)",
    "glow": "0 0 32px rgba(124,58,237,0.35)"
  }
}
```

- [ ] **Step 3: Написать build.ts — компиляция в CSS / TS / Tailwind preset**

Создать `packages/design-tokens/build.ts`:

```typescript
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import tokens from "./tokens.json" with { type: "json" };

type TokenValue = string | number;
type TokenTree = { [key: string]: TokenValue | TokenTree };

const ROOT = dirname(fileURLToPath(import.meta.url));
const DIST = resolve(ROOT, "dist");

mkdirSync(DIST, { recursive: true });

// --- 1. Flatten tokens for CSS custom properties ---
function flatten(node: TokenTree, prefix: string[] = []): Array<[string, TokenValue]> {
  return Object.entries(node).flatMap(([key, value]) => {
    const path = [...prefix, key];
    if (typeof value === "object" && value !== null) {
      return flatten(value as TokenTree, path);
    }
    return [[`--${path.join("-")}`, value]];
  });
}

const flat = flatten(tokens as TokenTree);

// --- 2. CSS file: :root { --color-app-dark-bg-primary: #0a0a0b; ... } ---
const css = `:root {\n${flat.map(([k, v]) => `  ${k}: ${v};`).join("\n")}\n}\n`;
writeFileSync(resolve(DIST, "tokens.css"), css);

// --- 3. CJS Tailwind preset ---
const tailwindPreset = `// AUTOGENERATED — do not edit. Source: tokens.json
module.exports = {
  theme: {
    extend: {
      colors: ${JSON.stringify(tokens.color, null, 2)},
      spacing: ${JSON.stringify(tokens.spacing, null, 2)},
      borderRadius: ${JSON.stringify(tokens.radius, null, 2)},
      fontFamily: ${JSON.stringify(tokens.font.family, null, 2)},
      fontSize: ${JSON.stringify(tokens.font.size, null, 2)},
      fontWeight: ${JSON.stringify(tokens.font.weight, null, 2)},
      lineHeight: ${JSON.stringify(tokens.font.leading, null, 2)},
      letterSpacing: ${JSON.stringify(tokens.font.tracking, null, 2)},
      boxShadow: ${JSON.stringify(tokens.shadow, null, 2)},
      transitionDuration: ${JSON.stringify(tokens.motion.duration, null, 2)},
      transitionTimingFunction: ${JSON.stringify(tokens.motion.easing, null, 2)},
    },
  },
};
`;
writeFileSync(resolve(DIST, "tailwind.cjs"), tailwindPreset);

console.log(`design-tokens: built ${flat.length} CSS vars + Tailwind preset → dist/`);
```

Создать `packages/design-tokens/src/index.ts`:

```typescript
import tokens from "../tokens.json" with { type: "json" };

export { tokens };
export type DesignTokens = typeof tokens;
```

- [ ] **Step 4: Запустить билд и проверить вывод**

Run:

```bash
cd packages/design-tokens
pnpm install
pnpm build
```

Expected: `dist/tokens.css` и `dist/tailwind.cjs` появились. Проверить вручную:

```bash
head -10 dist/tokens.css
# Expected: :root { --color-landing-bg-primary: #0a0a0a; ... }
head -20 dist/tailwind.cjs
# Expected: module.exports = { theme: { extend: { colors: { landing: {...}, app: {...} }, ... } } }
```

- [ ] **Step 5: Commit**

```bash
git add packages/design-tokens
git commit -m "feat(design-tokens): add @proshli/design-tokens package with build script"
```

---

## Task 2: `packages/ui-v2` skeleton + 5 primitives

Создаём пустую библиотеку компонентов с первыми пятью базовыми примитивами на Radix UI. Каждый компонент — controlled, styling через Tailwind с tokens из design-tokens, поведение через Radix.

**Files:**
- Create: `packages/ui-v2/package.json`
- Create: `packages/ui-v2/tsconfig.json` + `tsconfig.build.json`
- Create: `packages/ui-v2/tailwind.config.ts`
- Create: `packages/ui-v2/src/index.ts`
- Create: `packages/ui-v2/src/lib/cn.ts`
- Create: `packages/ui-v2/src/button.tsx` + `button.test.tsx`
- Create: `packages/ui-v2/src/input.tsx` + `input.test.tsx`
- Create: `packages/ui-v2/src/dialog.tsx` + `dialog.test.tsx`
- Create: `packages/ui-v2/src/sheet.tsx` + `sheet.test.tsx`
- Create: `packages/ui-v2/src/tooltip.tsx` + `tooltip.test.tsx`

- [ ] **Step 1: Создать package skeleton**

`packages/ui-v2/package.json`:

```json
{
  "name": "@proshli/ui-v2",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "exports": {
    ".": "./src/index.ts"
  },
  "scripts": {
    "lint": "eslint src",
    "type-check": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "@proshli/design-tokens": "workspace:*",
    "@radix-ui/react-dialog": "^1.1.2",
    "@radix-ui/react-slot": "^1.1.0",
    "@radix-ui/react-tooltip": "^1.1.4",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "lucide-react": "^0.460.0",
    "tailwind-merge": "^2.5.0"
  },
  "peerDependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@proshli/tsconfig": "workspace:*",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.1.0",
    "@types/react": "^19.0.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0"
  }
}
```

`packages/ui-v2/tsconfig.json`:

```json
{
  "extends": "@proshli/tsconfig/react-library.json",
  "include": ["src/**/*", "tailwind.config.ts"],
  "exclude": ["node_modules", "dist", "**/*.test.tsx"]
}
```

`packages/ui-v2/tailwind.config.ts`:

```typescript
import preset from "@proshli/design-tokens/tailwind";

import type { Config } from "tailwindcss";

export default {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [preset],
} satisfies Config;
```

`packages/ui-v2/src/lib/cn.ts`:

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** clsx + tailwind-merge: безопасное объединение className-ов с дедупом конфликтующих утилит. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
```

`packages/ui-v2/src/index.ts` (пока пустой, дополняется по мере добавления компонентов):

```typescript
export { Button, type ButtonProps } from "./button";
export { Input, type InputProps } from "./input";
export { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "./dialog";
export { Sheet, SheetContent, SheetHeader, SheetTitle } from "./sheet";
export { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";
export { cn } from "./lib/cn";
```

- [ ] **Step 2: Установить deps**

```bash
cd packages/ui-v2
pnpm install
```

Expected: успешная установка без peer-warnings (если есть warnings про React — это нормально, добавим React в monorepo root devDeps если ещё нет).

- [ ] **Step 3: Написать failing test для Button**

`packages/ui-v2/src/button.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./button";

describe("Button", () => {
  it("рендерит children как label", () => {
    render(<Button>Apply</Button>);
    expect(screen.getByRole("button", { name: "Apply" })).toBeInTheDocument();
  });

  it("выполняет onClick при клике", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    screen.getByRole("button").click();
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("применяет variant=primary стиль по умолчанию", () => {
    render(<Button>X</Button>);
    expect(screen.getByRole("button").className).toContain("bg-app-dark-accent");
  });

  it("применяет variant=ghost стиль", () => {
    render(<Button variant="ghost">X</Button>);
    expect(screen.getByRole("button").className).toContain("bg-transparent");
  });

  it("disabled блокирует клик", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick} disabled>X</Button>);
    screen.getByRole("button").click();
    expect(onClick).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 4: Запустить тест — он должен упасть**

```bash
cd packages/ui-v2
pnpm test button
```

Expected: FAIL — `Cannot find module './button'`.

- [ ] **Step 5: Написать минимальную реализацию Button**

`packages/ui-v2/src/button.tsx`:

```typescript
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
        secondary: "border border-app-dark-border bg-transparent text-app-dark-text-primary hover:bg-app-dark-bg-secondary",
        ghost: "bg-transparent text-app-dark-text-muted hover:text-app-dark-text-primary hover:bg-app-dark-bg-secondary",
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
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />;
  },
);
Button.displayName = "Button";
```

- [ ] **Step 6: Запустить тест — должен пройти**

```bash
pnpm test button
```

Expected: PASS — все 5 тестов зелёные.

- [ ] **Step 7: Повторить шаги 3-6 для Input**

`input.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Input } from "./input";

describe("Input", () => {
  it("рендерится с placeholder", () => {
    render(<Input placeholder="Введи email" />);
    expect(screen.getByPlaceholderText("Введи email")).toBeInTheDocument();
  });

  it("forwardRef работает", () => {
    let ref: HTMLInputElement | null = null;
    render(<Input ref={(el) => { ref = el; }} />);
    expect(ref).toBeInstanceOf(HTMLInputElement);
  });

  it("принимает type", () => {
    render(<Input type="email" data-testid="x" />);
    expect(screen.getByTestId("x")).toHaveAttribute("type", "email");
  });

  it("error-вариант добавляет красный border", () => {
    render(<Input error data-testid="x" />);
    expect(screen.getByTestId("x").className).toContain("border-red");
  });
});
```

`input.tsx`:

```typescript
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
```

Run: `pnpm test input` → PASS.

- [ ] **Step 8: Повторить для Dialog**

`dialog.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Dialog, DialogContent, DialogTitle } from "./dialog";

describe("Dialog", () => {
  it("открывается при open=true", () => {
    render(
      <Dialog open>
        <DialogContent>
          <DialogTitle>Привет</DialogTitle>
        </DialogContent>
      </Dialog>,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Привет")).toBeInTheDocument();
  });

  it("закрыт при open=false", () => {
    render(
      <Dialog open={false}>
        <DialogContent>
          <DialogTitle>Скрыт</DialogTitle>
        </DialogContent>
      </Dialog>,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
```

`dialog.tsx`:

```typescript
"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef, type HTMLAttributes } from "react";

import { cn } from "./lib/cn";

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogPortal = DialogPrimitive.Portal;

const DialogOverlay = forwardRef<ElementRef<typeof DialogPrimitive.Overlay>, ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Overlay
      ref={ref}
      className={cn(
        "fixed inset-0 z-50 bg-black/60 backdrop-blur-sm",
        "data-[state=open]:animate-in data-[state=closed]:animate-out",
        "data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0",
        className,
      )}
      {...props}
    />
  ),
);
DialogOverlay.displayName = "DialogOverlay";

export const DialogContent = forwardRef<ElementRef<typeof DialogPrimitive.Content>, ComponentPropsWithoutRef<typeof DialogPrimitive.Content>>(
  ({ className, children, ...props }, ref) => (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2",
          "rounded-xl border border-app-dark-border bg-app-dark-bg-secondary p-6 shadow-lg",
          "data-[state=open]:animate-in data-[state=closed]:animate-out",
          className,
        )}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded text-app-dark-text-muted hover:text-app-dark-text-primary">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPortal>
  ),
);
DialogContent.displayName = "DialogContent";

export const DialogHeader = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1.5 mb-4", className)} {...props} />
);

export const DialogTitle = forwardRef<ElementRef<typeof DialogPrimitive.Title>, ComponentPropsWithoutRef<typeof DialogPrimitive.Title>>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Title ref={ref} className={cn("text-18 font-semibold tracking-snug text-app-dark-text-primary", className)} {...props} />
  ),
);
DialogTitle.displayName = "DialogTitle";

export const DialogDescription = forwardRef<ElementRef<typeof DialogPrimitive.Description>, ComponentPropsWithoutRef<typeof DialogPrimitive.Description>>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Description ref={ref} className={cn("text-13 text-app-dark-text-muted", className)} {...props} />
  ),
);
DialogDescription.displayName = "DialogDescription";

export const DialogFooter = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex justify-end gap-2 mt-6", className)} {...props} />
);
```

Run: `pnpm test dialog` → PASS.

- [ ] **Step 9: Повторить для Sheet (правый side-panel, основа Cmd+J)**

`sheet.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Sheet, SheetContent, SheetTitle } from "./sheet";

describe("Sheet", () => {
  it("открывается справа", () => {
    render(
      <Sheet open>
        <SheetContent side="right">
          <SheetTitle>AI Assistant</SheetTitle>
        </SheetContent>
      </Sheet>,
    );
    expect(screen.getByText("AI Assistant")).toBeInTheDocument();
  });
});
```

`sheet.tsx`:

```typescript
"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from "react";

import { cn } from "./lib/cn";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;

const sheetVariants = cva(
  "fixed z-50 gap-4 bg-app-dark-bg-secondary p-6 shadow-lg border border-app-dark-border " +
    "data-[state=open]:animate-in data-[state=closed]:animate-out",
  {
    variants: {
      side: {
        top: "inset-x-0 top-0 border-b data-[state=open]:slide-in-from-top",
        bottom: "inset-x-0 bottom-0 border-t data-[state=open]:slide-in-from-bottom",
        left: "inset-y-0 left-0 h-full w-3/4 max-w-sm border-r data-[state=open]:slide-in-from-left",
        right: "inset-y-0 right-0 h-full w-3/4 max-w-md border-l data-[state=open]:slide-in-from-right",
      },
    },
    defaultVariants: { side: "right" },
  },
);

interface SheetContentProps extends ComponentPropsWithoutRef<typeof DialogPrimitive.Content>, VariantProps<typeof sheetVariants> {}

export const SheetContent = forwardRef<ElementRef<typeof DialogPrimitive.Content>, SheetContentProps>(
  ({ side = "right", className, children, ...props }, ref) => (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=closed]:animate-out" />
      <DialogPrimitive.Content ref={ref} className={cn(sheetVariants({ side }), className)} {...props}>
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded text-app-dark-text-muted hover:text-app-dark-text-primary">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  ),
);
SheetContent.displayName = "SheetContent";

export const SheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("flex flex-col gap-1.5 mb-4", className)} {...props} />
);

export const SheetTitle = forwardRef<ElementRef<typeof DialogPrimitive.Title>, ComponentPropsWithoutRef<typeof DialogPrimitive.Title>>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Title ref={ref} className={cn("text-18 font-semibold tracking-snug text-app-dark-text-primary", className)} {...props} />
  ),
);
SheetTitle.displayName = "SheetTitle";
```

Run: `pnpm test sheet` → PASS.

- [ ] **Step 10: Повторить для Tooltip**

`tooltip.test.tsx`:

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";

describe("Tooltip", () => {
  it("показывает контент при hover", async () => {
    render(
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger>Кнопка</TooltipTrigger>
          <TooltipContent>Подсказка</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    fireEvent.pointerEnter(screen.getByText("Кнопка"));
    expect(await screen.findByText("Подсказка")).toBeInTheDocument();
  });
});
```

`tooltip.tsx`:

```typescript
"use client";

import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { forwardRef, type ComponentPropsWithoutRef, type ElementRef } from "react";

import { cn } from "./lib/cn";

export const TooltipProvider = TooltipPrimitive.Provider;
export const Tooltip = TooltipPrimitive.Root;
export const TooltipTrigger = TooltipPrimitive.Trigger;

export const TooltipContent = forwardRef<ElementRef<typeof TooltipPrimitive.Content>, ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>>(
  ({ className, sideOffset = 4, ...props }, ref) => (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        ref={ref}
        sideOffset={sideOffset}
        className={cn(
          "z-50 overflow-hidden rounded-md border border-app-dark-border bg-app-dark-bg-tertiary px-3 py-1.5 text-12 text-app-dark-text-primary shadow-md",
          "data-[state=delayed-open]:animate-in data-[state=closed]:animate-out",
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  ),
);
TooltipContent.displayName = "TooltipContent";
```

Run: `pnpm test tooltip` → PASS.

- [ ] **Step 11: Запустить полный тест-сьют**

```bash
cd packages/ui-v2
pnpm test
```

Expected: все ~12-15 тестов проходят.

- [ ] **Step 12: Commit**

```bash
git add packages/ui-v2
git commit -m "feat(ui-v2): scaffold with Button, Input, Dialog, Sheet, Tooltip primitives"
```

---

## Task 3: Фикс AI guardrails — английские IT-роли

Quick-win. Закрывает баг, где `system analyst`, `data scientist`, `devops engineer` и подобные английские запросы режутся гейтом. Меняем код + добавляем регрессионные тесты.

**Files:**
- Modify: `apps/api/app/services/ai_guardrails.py:23-39`
- Create or Modify: `apps/api/tests/test_ai_guardrails.py`

- [ ] **Step 1: Найти / создать файл тестов**

```bash
ls apps/api/tests/test_ai_guardrails.py 2>/dev/null && echo "EXISTS" || echo "NEEDS CREATE"
```

Если файла нет — создать с заголовком pytest-конвенции:

```python
"""Tests for app.services.ai_guardrails: keyword gating + daily budget."""
from app.services.ai_guardrails import is_career_related
```

- [ ] **Step 2: Написать failing-тесты для английских IT-запросов**

В `apps/api/tests/test_ai_guardrails.py` добавить (или заменить, если уже что-то есть):

```python
import pytest

from app.services.ai_guardrails import is_career_related


class TestIsCareerRelated:
    """Гейт должен пропускать профессиональные запросы на ru и en, резать оффтоп."""

    @pytest.mark.parametrize(
        "query",
        [
            # Существующие русские (регрессия — не сломать)
            "ищу работу backend",
            "обнови резюме",
            "хочу зарплату 300к",
            "вакансия системного аналитика",
            # Новые английские IT-роли (это были false positives до фикса)
            "system analyst senior",
            "data scientist remote",
            "devops engineer with kubernetes",
            "qa lead manual or automation",
            "ml engineer pytorch",
            "fullstack developer node react",
            "ios mobile developer swift",
            "site reliability engineer",
            "product manager fintech",
            "ux designer figma",
            # Смешанные ru+en
            "ищу senior frontend позицию",
            "data engineer на удалёнке",
        ],
    )
    def test_passes_career_queries(self, query: str) -> None:
        assert is_career_related(query), f"должно быть career-related: {query!r}"

    @pytest.mark.parametrize(
        "query",
        [
            "расскажи анекдот",
            "что такое квантовая запутанность",
            "погода в москве",
            "как готовить борщ",
        ],
    )
    def test_blocks_offtopic(self, query: str) -> None:
        assert not is_career_related(query), f"должно быть отклонено: {query!r}"
```

- [ ] **Step 3: Запустить тесты — упадут на английских**

```bash
cd apps/api
uv run pytest tests/test_ai_guardrails.py -v
```

Expected: ~10 английских кейсов FAIL, русские PASS, оффтоп PASS.

- [ ] **Step 4: Расширить `CAREER_KEYWORDS`**

В `apps/api/app/services/ai_guardrails.py` заменить определение `CAREER_KEYWORDS` (строки 23-39) на:

```python
CAREER_KEYWORDS = {
    # --- Русские ключевые слова ---
    "работа",
    "вакансия",
    "вакансии",
    "резюме",
    "карьера",
    "отклик",
    "интервью",
    "собеседование",
    "зарплата",
    "оклад",
    "позиция",
    "должность",
    "аналитик",
    "разработчик",
    "программист",
    "инженер",
    "менеджер",
    "тестировщик",
    "удалёнка",
    "удаленка",
    # --- Английские уровни ---
    "junior",
    "middle",
    "senior",
    "lead",
    "principal",
    "staff",
    "intern",
    # --- Английские роли (общие) ---
    "developer",
    "engineer",
    "analyst",
    "manager",
    "designer",
    "scientist",
    "architect",
    "consultant",
    "specialist",
    "owner",
    # --- Английские роли (узкие) ---
    "fullstack",
    "full-stack",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "devops",
    "sre",
    "qa",
    "qae",
    "sdet",
    "pm",
    "product",
    "ux",
    "ui",
    "data",
    "ml",
    "ai",
    "mlops",
    "tech",
    "cto",
    "cpo",
    "cmo",
    "ceo",
    # --- Стеки / технологии ---
    "python",
    "java",
    "kotlin",
    "swift",
    "rust",
    "golang",
    "node",
    "nodejs",
    "react",
    "vue",
    "angular",
    "svelte",
    "ios",
    "android",
    "mobile",
    "web",
    "cloud",
    "aws",
    "gcp",
    "azure",
    "kubernetes",
    "docker",
    "linux",
    "sql",
    "nosql",
    "postgres",
    "mongo",
    "kafka",
    "spark",
    "hadoop",
    # --- Контекст найма ---
    "hire",
    "hiring",
    "job",
    "jobs",
    "position",
    "role",
    "remote",
    "hybrid",
    "office",
    "career",
    "salary",
    "compensation",
    "interview",
    "resume",
    "cv",
    "recruit",
    "recruiter",
    "employer",
    "employee",
}
```

- [ ] **Step 5: Запустить тесты — все проходят**

```bash
uv run pytest tests/test_ai_guardrails.py -v
```

Expected: все ~14 кейсов PASS, 4 оффтоп-кейса всё ещё блокируются.

- [ ] **Step 6: Запустить полный AI-test suite (регрессия)**

```bash
uv run pytest tests/ -k ai -v
```

Expected: все существующие тесты не сломались.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/services/ai_guardrails.py apps/api/tests/test_ai_guardrails.py
git commit -m "fix(ai-guardrails): accept English IT roles in career keyword gate

Whitelist had only 3 English keywords (python, frontend, backend) + junior/middle/senior.
Queries like 'system analyst', 'data scientist', 'devops engineer', 'qa lead' were
rejected as off-topic. Expanded to ~80 English IT terms covering roles, levels, stacks
and hiring context. Adds parametrized regression tests for 14 query patterns."
```

---

## Task 4: Caddy конфиг — подготовка к host-routing

Добавляем блок `app.proshli.ru` в Caddyfile, пока он проксирует на тот же `proshli-web` контейнер. Когда в Phase 1 появится Astro landing, мы переключим `proshli.ru` на новый контейнер, а `app.proshli.ru` останется указывать на (уже переписанный) Next.js. Это даёт нам возможность выкатить DNS-запись заранее, без авральной миграции в день launch.

**Files:**
- Modify: `deploy/Caddyfile`

- [ ] **Step 1: Прочитать текущий Caddyfile**

```bash
cat deploy/Caddyfile
```

Понять, какие хосты уже описаны (`proshli.ru`, `api.proshli.ru`, и т.д.) и какой паттерн использован (TLS automation, headers, log).

- [ ] **Step 2: Добавить новый блок для `app.proshli.ru`**

В конец `deploy/Caddyfile` добавить (точные директивы повторить из существующего `proshli.ru` блока):

```caddyfile
app.proshli.ru {
    # Phase 0: проксирует на тот же web-контейнер, что и proshli.ru.
    # В Phase 1 proshli.ru переедет на Astro landing, а app.proshli.ru
    # останется на Next.js — без даунтайма для пользователей в момент
    # переключения DNS.
    encode gzip zstd
    reverse_proxy proshli-web:3000 {
        header_up Host {host}
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }

    log {
        output stdout
        format json
    }
}
```

- [ ] **Step 3: Проверить синтаксис Caddyfile локально**

```bash
docker run --rm -v "$(pwd)/deploy/Caddyfile:/etc/caddy/Caddyfile" caddy:2-alpine caddy validate --config /etc/caddy/Caddyfile
```

Expected: `Valid configuration`.

- [ ] **Step 4: НЕ деплоить в прод**

Этот блок задеплоится вместе с Phase 1 (когда DNS-запись `app.proshli.ru` будет создана и Astro контейнер готов). Сейчас только коммит конфига.

- [ ] **Step 5: Commit**

```bash
git add deploy/Caddyfile
git commit -m "ops(caddy): add app.proshli.ru block for upcoming host-routing split

Caddy будет роутить proshli.ru на Astro landing (Phase 1) и app.proshli.ru
на Next.js — пока второй блок проксирует на тот же контейнер. Деплой
случится вместе с Phase 1; DNS запись создаётся оператором заранее."
```

---

## Task 5: Финальная проверка Phase 0

- [ ] **Step 1: Запустить весь монорепо-lint**

```bash
make lint
```

Expected: новые packages линтятся успешно. Если есть ошибки в `packages/design-tokens` или `packages/ui-v2` — починить inline.

- [ ] **Step 2: Запустить весь test-suite**

```bash
make test
```

Expected: всё зелёное. Новые ui-v2 тесты проходят, ai-guardrails тесты проходят, ничего из существующего не сломано.

- [ ] **Step 3: Push в main**

```bash
git push origin main
```

CI должна стать зелёной за ~5-7 минут. Если она красная — починить до Phase 1.

- [ ] **Step 4: Деплой AI-guardrails фикса в прод**

Только этот фикс деплоится — packages пока никем не используются, Caddy блок не запушен в прод-конфиг.

На сервере:

```bash
cd /opt/proshli && git pull && \
  docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod build api && \
  docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d api
```

- [ ] **Step 5: Smoke-test после деплоя**

```bash
make smoke-prod
```

Expected: 3/3 PASS. Дополнительно вручную: послать AI-чату запрос `system analyst senior remote` — должен ответить (а не отвергнуть).

- [ ] **Step 6: Mark Phase 0 как completed**

В `docs/superpowers/specs/2026-05-26-frontend-million-design.md` в секцию «Phasing» добавить статус-маркер:

```markdown
### Phase 0 — Foundation (Week 1) ✅ COMPLETED 2026-MM-DD
```

Commit:

```bash
git add docs/superpowers/specs/2026-05-26-frontend-million-design.md
git commit -m "docs(spec): mark Phase 0 (Foundation) as completed"
git push
```

---

## Risks & Mitigations

1. **`@radix-ui/react-slot` для `asChild` Button.** Если в существующем `packages/ui/` уже есть конфликтный экспорт `Button` — alias импорт или переименуй в `Button2` пока деприкейтишь старый. Phase 2 удалит старый `packages/ui`.

2. **Vitest setup для `packages/ui-v2`.** Если в монорепо ещё нет vitest config — добавь `packages/ui-v2/vitest.config.ts`:

   ```typescript
   import { defineConfig } from "vitest/config";

   export default defineConfig({
     test: { environment: "jsdom", globals: false, setupFiles: ["./vitest.setup.ts"] },
   });
   ```

   и `packages/ui-v2/vitest.setup.ts`:

   ```typescript
   import "@testing-library/jest-dom/vitest";
   ```

3. **Build-script на Windows.** `tsx build.ts` через ESM может ругаться на `import ... with { type: "json" }` — это Node.js 20.10+ синтаксис. Проверь: `node --version`. Если <20.10 — заменить на `import tokens from "./tokens.json"` + `assert { type: "json" }`.

4. **CI может не увидеть новые packages.** Проверить `.github/workflows/*.yml` — если CI matrix исключает `packages/*` или фильтрует по changed-paths, добавить новые директории.

5. **Caddy validate не работает локально.** Если `docker run --rm caddy:2-alpine` не запускается на машине разработчика — пропустить step, валидация случится при первом деплое (Caddy откажется стартовать с битым конфигом).

---

## Definition of Done

- [ ] `packages/design-tokens/dist/tokens.css` существует, содержит `~50+` CSS-vars
- [ ] `packages/design-tokens/dist/tailwind.cjs` экспортирует preset с `theme.extend.colors.app.dark.accent`
- [ ] `packages/ui-v2/src/{button,input,dialog,sheet,tooltip}.tsx` существуют, все тесты PASS
- [ ] `is_career_related("system analyst senior")` возвращает `True`
- [ ] `is_career_related("расскажи анекдот")` возвращает `False`
- [ ] `deploy/Caddyfile` содержит `app.proshli.ru` блок
- [ ] `make lint && make test` зелёные
- [ ] Прод-API отвечает на английские IT-запросы (verified через `make smoke-prod` + ручной AI-chat запрос)
- [ ] Phase 0 отмечена в spec как `✅ COMPLETED`

Готов к старту Phase 1 (Astro landing).
