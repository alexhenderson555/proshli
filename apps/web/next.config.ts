import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  // Workspace packages (`@otklik/ui`, `@otklik/shared-types`) ship raw
  // TypeScript sources rather than a pre-built `dist/`, so Next.js needs
  // to push them through its own SWC pipeline. Without this list, the
  // import would resolve to a `.ts` file Next refuses to compile.
  transpilePackages: ["@otklik/ui", "@otklik/shared-types"],
};

export default nextConfig;
