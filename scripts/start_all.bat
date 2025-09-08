@echo off
REM DocExtract Complete System Start Script (Windows)
REM Usage: start_all.bat [dev|prod]

setlocal enabledelayedexpansion

REM Error handling
if "%ERRORLEVEL%" neq "0" exit /b %ERRORLEVEL%

REM Color definitions (Windows compatible)
set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "PURPLE=[95m"
set "NC=[0m"

REM Default values
set "MODE=%1"
if "%MODE%"=="" set "MODE=dev"
set "CONDA_ENV=%CONDA_ENV%"
if "%CONDA_ENV%"=="" set "CONDA_ENV=DocExtract"

echo %PURPLE%DocExtract Complete System Starting%NC%
echo %YELLOW%Mode: %MODE%%NC%
echo %YELLOW%Conda Environment: %CONDA_ENV%%NC%
echo.

REM Get project directories
for %%i in ("%~dp0") do set "SCRIPT_DIR=%%~fi"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"

echo %BLUE%Project Root: %PROJECT_ROOT%%NC%

REM Check script files
set "BACKEND_SCRIPT=%SCRIPT_DIR%start_backend.bat"
set "FRONTEND_SCRIPT=%SCRIPT_DIR%start_frontend.bat"

if not exist "%BACKEND_SCRIPT%" (
    echo %RED%ERROR: Backend script not found: %BACKEND_SCRIPT%%NC%
    pause
    exit /b 1
)

if not exist "%FRONTEND_SCRIPT%" (
    echo %RED%ERROR: Frontend script not found: %FRONTEND_SCRIPT%%NC%
    pause
    exit /b 1
)

REM Create PID directory
set "PID_DIR=%PROJECT_ROOT%\.pids"
if not exist "%PID_DIR%" mkdir "%PID_DIR%"

REM Port conflict check
set "BACKEND_PORT=%BACKEND_PORT%"
if "%BACKEND_PORT%"=="" set "BACKEND_PORT=58000"
set "FRONTEND_PORT=%FRONTEND_PORT%"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=8088"

echo %YELLOW%Checking port usage...%NC%

REM Check backend port
netstat -an | findstr ":%BACKEND_PORT% " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%WARNING: Backend port %BACKEND_PORT% is already in use%NC%
    set /p "CONFIRM=Continue anyway? (y/N): "
    if /i not "!CONFIRM!"=="y" (
        exit /b 1
    )
)

REM Check frontend port
netstat -an | findstr ":%FRONTEND_PORT% " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%WARNING: Frontend port %FRONTEND_PORT% is already in use%NC%
    set /p "CONFIRM=Continue anyway? (y/N): "
    if /i not "!CONFIRM!"=="y" (
        exit /b 1
    )
)

echo.
echo %GREEN%Starting servers sequentially...%NC%
echo.

REM Start backend server
echo %BLUE%1. Starting backend server...%NC%
start "DocExtract Backend" /MIN cmd /c ""%BACKEND_SCRIPT%" %MODE% > "%PROJECT_ROOT%\backend.log" 2>&1"

REM Wait for backend to start
echo %YELLOW%Waiting for backend server to start...%NC%
timeout /t 10 /nobreak >nul

REM Check backend API response
set "BACKEND_READY=false"
for /L %%i in (1,1,15) do (
    curl -s http://localhost:%BACKEND_PORT%/ >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo %GREEN%Backend server started successfully%NC%
        set "BACKEND_READY=true"
        goto :backend_ready
    )
    timeout /t 2 /nobreak >nul
)

:backend_ready
if "%BACKEND_READY%"=="false" (
    echo %RED%ERROR: Backend server failed to start%NC%
    echo %YELLOW%Check log: type "%PROJECT_ROOT%\backend.log"%NC%
    pause
    exit /b 1
)

timeout /t 3 /nobreak >nul

REM Start frontend server
echo %BLUE%2. Starting frontend server...%NC%
start "DocExtract Frontend" /MIN cmd /c ""%FRONTEND_SCRIPT%" %MODE% > "%PROJECT_ROOT%\frontend.log" 2>&1"

REM Wait for frontend to start
echo %YELLOW%Waiting for frontend server to start...%NC%
timeout /t 15 /nobreak >nul

echo %GREEN%Frontend server started%NC%

echo.
echo %PURPLE%DocExtract system started successfully!%NC%
echo.
echo %BLUE%Service Information:%NC%
echo %GREEN%  Backend API: http://localhost:%BACKEND_PORT%%NC%
echo %GREEN%  API Documentation: http://localhost:%BACKEND_PORT%/docs%NC%
echo %GREEN%  Frontend Web App: http://localhost:%FRONTEND_PORT%%NC%
echo.
echo %BLUE%Log Files:%NC%
echo %YELLOW%  Backend: type "%PROJECT_ROOT%\backend.log"%NC%
echo %YELLOW%  Frontend: type "%PROJECT_ROOT%\frontend.log"%NC%
echo.
echo %BLUE%Management Commands:%NC%
echo %YELLOW%  Stop system: stop_all.bat%NC%
echo %YELLOW%  Check status: status.bat%NC%
echo.
echo %RED%To stop the system, run: stop_all.bat%NC%
echo.
pause