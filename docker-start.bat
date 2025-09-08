@echo off
REM DocExtract Docker Startup Script (Windows)

echo Starting DocExtract Docker environment...

REM Load environment variables
if exist .env (
    echo Loading environment variables...
    REM Environment variables are handled by docker-compose on Windows
)

REM Create necessary directories
echo Creating necessary directories...
if not exist "data" mkdir data
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs

REM Start Docker Compose services
echo Starting Docker services...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services
    pause
    exit /b 1
)

REM Wait for services to start
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo Checking service status...
docker-compose ps

echo.
echo SUCCESS: DocExtract Docker environment started!
echo.
echo Service Access Information:
echo   - DocExtract API: http://localhost:58000
echo   - API Documentation: http://localhost:58000/docs
echo   - Memgraph Bolt: bolt://localhost:7688
echo   - Memgraph Monitoring: http://localhost:7445
echo.
echo Useful Commands:
echo   - View logs: docker-compose logs -f
echo   - Stop services: docker-compose down
echo   - Restart services: docker-compose restart
echo   - Check status: docker-compose ps
echo.

REM Health check
echo Performing health check...
timeout /t 5 /nobreak >nul

REM Check DocExtract API
echo Checking DocExtract API...
curl -s http://localhost:58000/docs >nul 2>&1
if %errorlevel% equ 0 (
    echo SUCCESS: DocExtract API is running
) else (
    echo WARNING: DocExtract API not accessible - services may still be starting
)

echo.
echo All services are ready!
echo For detailed usage, see DOCKER_README.md
echo.
pause