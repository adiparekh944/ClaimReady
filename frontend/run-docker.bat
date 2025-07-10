@echo off
setlocal enabledelayedexpansion

echo 🚀 Building and running ClaimReady Frontend with Docker

REM Stop and remove existing container if it exists
echo 🧹 Cleaning up existing container...
docker stop claimready-frontend 2>nul
docker rm claimready-frontend 2>nul

REM Build the Docker image
echo 📦 Building Docker image...
docker build -t claimready-frontend .

if %errorlevel% neq 0 (
    echo ❌ Docker build failed!
    echo This might be due to missing dependencies or network issues.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

REM Run the container
echo 🚀 Starting container...
docker run -d ^
    --name claimready-frontend ^
    -p 3000:3000 ^
    --restart unless-stopped ^
    claimready-frontend

if %errorlevel% equ 0 (
    echo ✅ Frontend is running!
    echo 🌐 Access your app: http://localhost:3000
    echo 📝 To view logs: docker logs -f claimready-frontend
    echo 🛑 To stop: docker stop claimready-frontend
    echo 🗑️  To remove: docker rm claimready-frontend
    echo.
    echo 🔗 Make sure your backend is also running at http://localhost:8080
) else (
    echo ❌ Failed to start container!
    echo Check the logs with: docker logs claimready-frontend
    pause
    exit /b 1
)

pause 