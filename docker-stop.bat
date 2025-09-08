@echo off
REM DocExtract Docker Stop Script (Windows)

echo Stopping DocExtract Docker environment...

REM Stop Docker Compose services
echo Stopping Docker services...
docker-compose down

if %errorlevel% neq 0 (
    echo ERROR: Failed to stop Docker services
    pause
    exit /b 1
)

echo.
echo Optional cleanup options:
echo   Full cleanup (images, volumes): docker-clean.bat
echo   View logs only: docker-compose logs
echo.
echo SUCCESS: DocExtract Docker environment stopped!
echo.
pause