@echo off
REM DocExtract Docker Cleanup Script (Windows)

echo Cleaning up DocExtract Docker environment...

REM Confirmation message
set /p CONFIRM="WARNING: Delete all containers, images, and volumes? (y/N): "
if /i not "%CONFIRM%"=="y" (
    echo Cleanup operation cancelled.
    pause
    exit /b 1
)

REM Stop and remove services
echo Stopping Docker services and removing containers...
docker-compose down -v --remove-orphans

if %errorlevel% neq 0 (
    echo ERROR: Failed to stop Docker services
    pause
    exit /b 1
)

REM Remove images
echo Removing DocExtract related images...
for /f "tokens=3" %%i in ('docker images ^| findstr /i "docextract memgraph"') do (
    docker rmi -f %%i 2>nul
)

REM Remove volumes
echo Removing DocExtract related volumes...
for /f "tokens=2" %%i in ('docker volume ls ^| findstr /i "docextract memgraph"') do (
    docker volume rm %%i 2>nul
)

REM Remove networks
echo Removing DocExtract networks...
for /f "tokens=1" %%i in ('docker network ls ^| findstr docextract') do (
    docker network rm %%i 2>nul
)

REM Clean up unused resources
echo Cleaning up unused Docker resources...
docker system prune -f

echo.
echo SUCCESS: DocExtract Docker environment completely cleaned up!
echo To restart: docker-start.bat
echo.
pause