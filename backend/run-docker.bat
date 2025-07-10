@echo off
setlocal enabledelayedexpansion

echo 🚀 Building and running ClaimReady Backend with Docker

REM Check if .env file exists
if not exist .env (
    echo ⚠️  No .env file found. Creating from template...
    copy .env.example .env
    echo ❌ Please edit .env file with your actual API keys before running again!
    echo Required API keys:
    echo   - NEXT_PUBLIC_SUPABASE_URL
    echo   - SUPABASE_SERVICE_ROLE_KEY
    echo   - GEMINI_API_KEY
    echo   - ELEVEN_LABS_API_KEY
    echo   - OPENAI_API_KEY
    pause
    exit /b 1
)

REM Stop and remove existing container if it exists
echo 🧹 Cleaning up existing container...
docker stop claimready-backend 2>nul
docker rm claimready-backend 2>nul

REM Build the Docker image
echo 📦 Building Docker image...
docker build -t claimready-backend .

if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    echo This might be due to missing dependencies or network issues.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

REM Create directories if they don't exist
if not exist frames mkdir frames
if not exist temp_uploads mkdir temp_uploads

REM Run the container
echo 🚀 Starting container...
docker run -d ^
    --name claimready-backend ^
    -p 8080:8080 ^
    --env-file .env ^
    -v %cd%/frames:/app/frames ^
    -v %cd%/temp_uploads:/app/temp_uploads ^
    --restart unless-stopped ^
    claimready-backend

if %errorlevel% equ 0 (
    echo ✅ Backend is running!
    echo 🌐 Health check: http://localhost:8080/health
    echo 📊 API endpoints: http://localhost:8080/api/*
    echo 📝 To view logs: docker logs -f claimready-backend
    echo 🛑 To stop: docker stop claimready-backend
    echo 🗑️  To remove: docker rm claimready-backend
    echo.
    echo ⚠️  Note: Audio features may not work in Docker container
    echo     This is normal - the backend will still function for API calls
) else (
    echo ❌ Failed to start container!
    echo Check the logs with: docker logs claimready-backend
    pause
    exit /b 1
)

pause 