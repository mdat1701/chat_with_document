# Image front-end tĩnh (SADD §1.3, §4.4, T-003) — build rồi phục vụ
# qua nginx, không chạy Node ở runtime.

FROM node:22-alpine AS builder
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
# nginx-unprivileged đã chạy bằng user không phải root (uid 101) sẵn.
EXPOSE 8080
