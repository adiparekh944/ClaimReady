# Frontend Docker Setup

This directory contains the Docker configuration for the ClaimReady frontend application.

## Prerequisites

- Docker Desktop installed and running
- Node.js 18+ (for local development)

## Building and Running

### Option 1: Using Docker Compose (Recommended)

```bash
# Build and start the frontend container
docker-compose up --build

# Run in detached mode
docker-compose up -d --build

# Stop the container
docker-compose down
```

### Option 2: Using Docker directly

```bash
# Build the Docker image
docker build -t claimready-frontend .

# Run the container
docker run -p 3000:3000 claimready-frontend
```

## Accessing the Application

Once the container is running, the frontend will be available at:
- http://localhost:3000

## Development

For local development without Docker:

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

## Environment Variables

The following environment variables can be configured:

- `NODE_ENV`: Set to `production` for production builds
- `NEXT_TELEMETRY_DISABLED`: Set to `1` to disable Next.js telemetry
- `PORT`: Port number (default: 3000)
- `HOSTNAME`: Hostname to bind to (default: 0.0.0.0)
- `NEXT_PUBLIC_BACKEND_URL`: Backend API URL (default: http://localhost:8080)

### Important: Backend URL Configuration

The frontend needs to know where your backend is running. By default, it expects the backend to be on `http://localhost:8080`. 

**For Docker Compose setup:**
```bash
# Set the backend URL to point to your backend container
NEXT_PUBLIC_BACKEND_URL=http://backend:8080
```

**For local development:**
```bash
# Backend running locally
NEXT_PUBLIC_BACKEND_URL=http://localhost:8080
```

**For production:**
```bash
# Backend running on a different server
NEXT_PUBLIC_BACKEND_URL=https://your-backend-domain.com
```

## Docker Image Details

- **Base Image**: Node.js 18 Alpine
- **Multi-stage Build**: Optimized for production with minimal image size
- **Security**: Runs as non-root user (`nextjs`)
- **Performance**: Uses Next.js standalone output for faster startup

## Troubleshooting

1. **Docker Desktop not running**: Make sure Docker Desktop is started before running commands
2. **Port conflicts**: If port 3000 is already in use, modify the port mapping in docker-compose.yml
3. **Build failures**: Ensure all dependencies are properly listed in package.json
