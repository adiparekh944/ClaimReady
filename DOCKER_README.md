# ClaimReady Docker Setup

This guide covers running both the frontend and backend of ClaimReady using Docker.

## Quick Start

### Option 1: Run Everything with Docker Compose (Recommended)

1. **Set up environment variables:**
   ```bash
   # Copy the backend environment file
   cp backend/.env.example backend/.env
   
   # Edit backend/.env with your actual API keys
   ```

2. **Run both services:**
   ```bash
   docker-compose up --build
   ```

3. **Access your application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8080
   - Backend Health: http://localhost:8080/health

### Option 2: Run Services Individually

#### Backend Only
```bash
cd backend
run-docker.bat
```

#### Frontend Only
```bash
cd frontend
run-docker.bat
```

## Environment Variables

### Backend (.env file in backend directory)
```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
GEMINI_API_KEY=your_gemini_api_key_here
ELEVEN_LABS_API_KEY=your_eleven_labs_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### Frontend (automatically gets from backend .env)
The frontend will automatically receive these environment variables:
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_BACKEND_URL` (set to http://localhost:8080)

## Docker Configuration Details

### Backend Dockerfile
- **Base Image**: Python 3.10 slim
- **Dependencies**: OpenCV, audio processing, ML libraries
- **Port**: 8080
- **Features**: 
  - Multi-stage build for optimization
  - Non-root user for security
  - Health checks
  - Volume mounts for file storage

### Frontend Dockerfile
- **Base Image**: Node.js 20 Alpine
- **Framework**: Next.js 15
- **Port**: 3000
- **Features**:
  - Multi-stage build for smaller image size
  - Standalone output for production
  - Non-root user for security
  - Optimized for production

## Useful Commands

### Docker Compose
```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart backend
docker-compose restart frontend
```

### Individual Containers
```bash
# View logs
docker logs -f claimready-backend
docker logs -f claimready-frontend

# Stop containers
docker stop claimready-backend claimready-frontend

# Remove containers
docker rm claimready-backend claimready-frontend

# Access container shell
docker exec -it claimready-backend bash
docker exec -it claimready-frontend sh
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check what's using the ports
   netstat -ano | findstr :3000
   netstat -ano | findstr :8080
   
   # Or use different ports in docker-compose.yml
   ```

2. **Build Failures**
   ```bash
   # Clean build cache
   docker system prune -a
   docker-compose build --no-cache
   ```

3. **Memory Issues**
   - Backend needs at least 2GB RAM for ML models
   - Frontend needs at least 512MB RAM
   - Adjust limits in docker-compose.yml if needed

4. **Environment Variables**
   ```bash
   # Check if .env file exists
   ls backend/.env
   
   # Verify environment variables are loaded
   docker-compose config
   ```

### Health Checks

Both services include health checks:
- Backend: http://localhost:8080/health
- Frontend: http://localhost:3000

If health checks fail:
```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs backend
docker-compose logs frontend
```

## Development vs Production

### Development
For development, you can override the CMD in docker-compose.yml:

```yaml
services:
  frontend:
    # ... other config
    command: ["npm", "run", "dev"]
  
  backend:
    # ... other config
    command: ["python", "api.py"]
```

### Production
The current setup is optimized for production with:
- Multi-stage builds
- Non-root users
- Health checks
- Resource limits
- Automatic restarts

## File Structure
```
ClaimReady/
├── docker-compose.yml          # Main orchestration file
├── DOCKER_README.md           # This file
├── backend/
│   ├── Dockerfile             # Backend container
│   ├── run-docker.bat         # Backend run script
│   ├── .env                   # Backend environment variables
│   └── ...
└── frontend/
    ├── Dockerfile             # Frontend container
    ├── run-docker.bat         # Frontend run script
    ├── .dockerignore          # Frontend build exclusions
    └── ...
```

## Next Steps

1. **Set up your environment variables** in `backend/.env`
2. **Run the application** with `docker-compose up --build`
3. **Access your app** at http://localhost:3000
4. **Monitor logs** with `docker-compose logs -f`

Your ClaimReady application is now running in Docker! 🎉 