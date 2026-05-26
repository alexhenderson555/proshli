# Multi-stage build for Astro static output.
# Final image: nginx:alpine serving pre-built dist/.

# --- Stage 1: build ---
FROM node:22-alpine AS builder

WORKDIR /workspace

# pnpm via corepack
RUN corepack enable && corepack prepare pnpm@10.10.0 --activate

# Copy lockfile + workspace config
COPY pnpm-workspace.yaml pnpm-lock.yaml package.json ./

# Copy dependent packages
COPY packages/design-tokens/package.json packages/design-tokens/
COPY packages/tsconfig/package.json packages/tsconfig/

# Copy landing
COPY apps/landing/package.json apps/landing/

# Install
RUN pnpm install --frozen-lockfile --filter @proshli/landing...

# Copy source and build
COPY packages packages
COPY apps/landing apps/landing

RUN pnpm --filter @proshli/design-tokens build && \
    pnpm --filter @proshli/landing build

# --- Stage 2: nginx serve ---
FROM nginx:1.27-alpine

COPY --from=builder /workspace/apps/landing/dist /usr/share/nginx/html
COPY apps/landing/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
