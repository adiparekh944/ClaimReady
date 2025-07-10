@echo off
echo Building ClaimReady Frontend...

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found in current directory
    echo Please make sure you're in the root directory with the .env file
    pause
    exit /b 1
)

REM Build the Docker image with environment variables
echo Building Docker image...
docker build ^
  -f frontend/Dockerfile ^
  --build-arg NEXT_PUBLIC_SUPABASE_URL=https://hjomhelzgvdmjyhijyxr.supabase.co ^
  --build-arg NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imhqb21oZWx6Z3ZkbWp5aGlqeXhyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDcwODU1MTMsImV4cCI6MjA2MjY2MTUxM30.D1pwL5D6uAv_e3hNkmb91ju2JsTDBf1xPk3OgJ-_71w ^
  --build-arg NEXT_PUBLIC_BACKEND_URL=http://localhost:8080 ^
  -t claimready-frontend .

if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    pause
    exit /b 1
)

echo Build completed successfully!
echo.
echo To run the container:
echo docker run -d --name claimready-frontend -p 3000:3000 claimready-frontend
echo.
echo To stop and remove the container:
echo docker stop claimready-frontend
echo docker rm claimready-frontend
echo.
pause 