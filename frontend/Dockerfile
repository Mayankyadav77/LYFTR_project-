# Multi-stage Dockerfile for React + Vite Frontend

# Stage 1: Build static assets
FROM node:20-alpine as builder

WORKDIR /app

# Accept build arguments for Vite environment variables
ARG VITE_API_URL=https://lyftr-project.onrender.com
ARG VITE_API_BASE_URL=https://lyftr-project.onrender.com
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve with lightweight Nginx
FROM nginx:alpine as runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
