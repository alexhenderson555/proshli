import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  // Workspace packages (`@proshli/ui`, `@proshli/shared-types`) ship raw
  // TypeScript sources rather than a pre-built `dist/`, so Next.js needs
  // to push them through its own SWC pipeline. Without this list, the
  // import would resolve to a `.ts` file Next refuses to compile.
  transpilePackages: ["@proshli/ui", "@proshli/shared-types"],
};

// next-intl plugin: wires `i18n/request.ts` as the per-request config
// source for server components (`getTranslations`, `getMessages`, ...).
const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

export default withNextIntl(nextConfig);
