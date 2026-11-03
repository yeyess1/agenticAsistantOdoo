# Stage 1: Building the code
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the application
# We use --no-lint to skip linting during build if it's too strict
RUN npm run build

# Stage 2: Run the code
FROM node:20-slim AS runner

WORKDIR /app

# Set environment
ENV NODE_ENV production

# Copy necessary files from builder
COPY --from=builder /app/next.config.ts ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose the port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
