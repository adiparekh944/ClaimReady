# Use official Node image
FROM node:20

# Set working directory
WORKDIR /app

# Copy package files first (leverages Docker cache better)
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm install

# Copy the entire frontend codebase into image
COPY frontend/ .

# Copy production environment variables file (important for next build)
COPY frontend/.env .env

# Build Next.js app
RUN npm run build

# Expose port
EXPOSE 3000

# Start Next.js server
CMD ["npm", "start"]