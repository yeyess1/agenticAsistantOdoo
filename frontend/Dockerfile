# syntax=docker/dockerfile:1
# frontend: Next.js 16 with `output: "standalone"` (U-13, D-10). No node_modules at runtime.
ARG NODE_IMAGE=node:22.21.1-alpine3.22

# --- deps: npm ci, cached until package-lock.json changes --------------------------------
FROM ${NODE_IMAGE} AS deps
WORKDIR /app
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    npm ci --no-audit --no-fund

# --- build: next build -> .next/standalone + .next/static ---------------------------------
FROM ${NODE_IMAGE} AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# --- runtime: standalone server only, non-root ------------------------------------------
FROM ${NODE_IMAGE} AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN addgroup -S -g 10001 app && adduser -S -u 10001 -G app -H -s /sbin/nologin app
COPY --from=build --chown=10001:10001 /app/.next/standalone ./
COPY --from=build --chown=10001:10001 /app/.next/static ./.next/static
COPY --from=build --chown=10001:10001 /app/public ./public
USER 10001:10001
EXPOSE 3000
ENTRYPOINT ["node", "server.js"]
