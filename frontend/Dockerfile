FROM node:22-alpine AS builder
RUN corepack enable && corepack prepare pnpm@10.26.2 --activate
WORKDIR /app
ENV CI=true
ENV NO_UPDATE_NOTIFIER=true
COPY package.json pnpm-lock.yaml .npmrc ./
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
  set -eux; \
  pnpm config set fetch-retries 5; \
  pnpm config set fetch-retry-factor 2; \
  pnpm config set fetch-retry-mintimeout 10000; \
  pnpm config set fetch-retry-maxtimeout 120000; \
  pnpm config set fetch-timeout 300000; \
  pnpm config set network-concurrency 8; \
  pnpm config set child-concurrency 4; \
  pnpm config set prefer-offline true; \
  pnpm config set package-import-method copy; \
  pnpm config set verify-deps-before-run false; \
  attempt=1; \
  until [ "$attempt" -gt 3 ]; do \
  echo "pnpm fetch/install attempt ${attempt}/3"; \
  if pnpm fetch --frozen-lockfile --reporter=append-only \
  && pnpm install --frozen-lockfile --offline --reporter=append-only; then \
  break; \
  fi; \
  if [ "$attempt" -eq 3 ]; then \
  exit 1; \
  fi; \
  attempt=$((attempt + 1)); \
  sleep 8; \
  done
COPY . .
RUN pnpm run --config.verify-deps-before-run=false build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
