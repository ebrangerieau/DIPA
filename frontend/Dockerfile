# Multi-stage build pour optimisation
FROM node:24-alpine AS base

WORKDIR /app

# Stage de développement (Vite, rechargement à chaud)
FROM base AS development

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]

# Stage de build
FROM base AS build

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage de production : Nginx sans privilèges root (port 8080)
FROM nginxinc/nginx-unprivileged:stable-alpine AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/ || exit 1
