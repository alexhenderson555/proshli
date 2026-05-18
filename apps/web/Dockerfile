# Multi-stage build for the Next.js app. We produce a Node-based runtime
# image that runs `next start`. Once Wave 10 lands, this can swap to the
# standalone output (`output: 'standalone'`) for an even smaller image.

FROM node:22-alpine AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# ---------- deps ----------
FROM base AS deps
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages ./packages
RUN pnpm install --frozen-lockfile

# ---------- build ----------
FROM base AS build
WORKDIR /repo
# `NEXT_PUBLIC_*` env vars are inlined by Next.js at *build* time — the
# runtime container's env is too late, the value is already baked into
# the static JS chunks. We accept the API URL as a build arg, default
# it to the prod canonical, and re-export it as an env so `next build`
# picks it up. compose passes the real value via `build.args`.
ARG NEXT_PUBLIC_API_URL=https://proshli.ru/api
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
# Stage the source first, then layer the installed node_modules on top
# so the deps-stage installs (including symlinks into packages/*) survive
# the COPY. Without this `COPY . .` would land *after* the modules copy
# and could shadow workspace node_modules that next build needs.
COPY . .
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/apps/web/node_modules ./apps/web/node_modules
COPY --from=deps /repo/packages ./packages
RUN pnpm --filter @proshli/web build

# ---------- runtime ----------
FROM node:22-alpine AS runtime
# Mirror the monorepo layout under /repo so pnpm's relative symlinks
# (apps/web/node_modules/<pkg> -> ../../../node_modules/.pnpm/...) stay
# valid. Anything else (flatten, copy in /app, etc) breaks the pnpm
# store path.
WORKDIR /repo/apps/web
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Workspace plumbing: root manifest, lockfile, hoisted modules,
# .pnpm store all live at /repo.
COPY --from=build /repo/package.json /repo/pnpm-workspace.yaml /repo/.npmrc /repo/
COPY --from=build /repo/node_modules /repo/node_modules
COPY --from=build /repo/packages /repo/packages

# The actual web app — built artifacts, manifest, and its own
# node_modules (whose entries are symlinks back into /repo/node_modules
# /.pnpm/...).
COPY --from=build /repo/apps/web/.next ./.next
COPY --from=build /repo/apps/web/public ./public
COPY --from=build /repo/apps/web/package.json ./package.json
COPY --from=build /repo/apps/web/node_modules ./node_modules

EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "--port", "3000"]
