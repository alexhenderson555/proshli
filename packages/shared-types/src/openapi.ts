// Placeholder until Wave 10 runs `pnpm -F @otklik/shared-types gen`
// against the live API. Once generated, every named export below will be
// replaced by codegen output. We keep the empty shapes here so that other
// packages can `import type { paths } from "@otklik/shared-types"` today
// without a hard compile error.

export type paths = Record<string, unknown>;
export type components = { schemas: Record<string, unknown> };
export type operations = Record<string, unknown>;
