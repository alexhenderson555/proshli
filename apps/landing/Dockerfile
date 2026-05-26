# Multi-stage build for Astro static output.
# Final image: nginx:alpine serving pre-built dist/.

# --- Stage 1: build ---
FROM node:22-alpine AS builder

WORKDIR /workspace

# pnpm via corepack
RUN corepack enable && corepack prepare pnpm@10.10.0 --activate

# Use hoisted node_modules layout in Docker to avoid pnpm symlink issues.
RUN echo "node-linker=hoisted" > .npmrc

# Copy workspace root files
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./

# Copy ALL JS/TS workspace package.json files so the lockfile resolves.
COPY packages/design-tokens/package.json packages/design-tokens/
COPY packages/tsconfig/package.json packages/tsconfig/
COPY packages/ui-v2/package.json packages/ui-v2/
COPY packages/ui/package.json packages/ui/
COPY packages/shared-types/package.json packages/shared-types/
COPY packages/eslint-config/package.json packages/eslint-config/
COPY apps/landing/package.json apps/landing/
COPY apps/web/package.json apps/web/

# Install with hoisted layout — no symlink resolution issues.
RUN pnpm install --frozen-lockfile

# Copy only the sources we need for the landing build.
COPY packages/design-tokens packages/design-tokens
COPY packages/tsconfig packages/tsconfig
COPY apps/landing apps/landing

# Build design-tokens first (landing depends on its dist/), then landing.
RUN pnpm --filter @proshli/design-tokens build && \
    pnpm --filter @proshli/landing build

# --- Stage 2: nginx serve ---
FROM nginx:1.27-alpine

COPY --from=builder /workspace/apps/landing/dist /usr/share/nginx/html
COPY apps/landing/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
