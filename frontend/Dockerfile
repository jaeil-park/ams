# ─── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
LABEL stage=builder

WORKDIR /app

# package.json 먼저 복사 → 의존성 레이어 캐시 최적화
COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile

# 소스코드 복사 후 프로덕션 빌드
COPY . .
RUN npm run build

# ─── Stage 2: Serve ──────────────────────────────────────────────────────────
FROM nginx:1.25-alpine AS runner

# 보안: 불필요한 기본 nginx 설정 제거
RUN rm /etc/nginx/conf.d/default.conf

# 빌드 결과물 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# 커스텀 nginx 설정 복사 (API 프록시 + history mode + gzip)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
