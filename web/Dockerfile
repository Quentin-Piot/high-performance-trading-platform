# Multi-stage build for Vue.js frontend
FROM node:20 AS builder

WORKDIR /app

# Set Node.js memory limits to prevent OOM crashes
ENV NODE_OPTIONS="--max-old-space-size=2048"

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm --version
RUN pnpm install --frozen-lockfile

# Copy source code
COPY . .

# Build-time API base URL (used by Vite)
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Build the application with memory optimization
RUN NODE_OPTIONS="--max-old-space-size=2048" pnpm run build

# Production stage with Nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
