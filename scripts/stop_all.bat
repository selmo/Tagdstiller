@echo off
REM DocExtract System Stop Script (Windows)
REM Usage: stop_all.bat

setlocal enabledelayedexpansion

REM Color definitions (Windows compatible)
set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "PURPLE=[95m"
set "NC=[0m"

echo %PURPLE%DocExtract System Stop%NC%
echo.

REM Get project directories
for %%i in ("%~dp0") do set "SCRIPT_DIR=%%~fi"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"
set "PID_DIR=%PROJECT_ROOT%\.pids"

echo %BLUE%Project Root: %PROJECT_ROOT%%NC%

REM Stop processes by window title (since we started with titles)
set "stopped_any=false"

echo %YELLOW%Stopping DocExtract processes...%NC%

REM Stop backend process
tasklist /FI "WINDOWTITLE eq DocExtract Backend*" 2>nul | findstr /I cmd >nul
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%Stopping backend server...%NC%
    taskkill /FI "WINDOWTITLE eq DocExtract Backend*" /T /F >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo %GREEN%Backend server stopped successfully%NC%
        set "stopped_any=true"
    )
)

REM Stop frontend process
tasklist /FI "WINDOWTITLE eq DocExtract Frontend*" 2>nul | findstr /I cmd >nul
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%Stopping frontend server...%NC%
    taskkill /FI "WINDOWTITLE eq DocExtract Frontend*" /T /F >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo %GREEN%Frontend server stopped successfully%NC%
        set "stopped_any=true"
    )
)

REM Stop processes by port
echo %BLUE%Checking port-based processes...%NC%

REM Backend port (58000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":58000 "') do (
    set "PID=%%a"
    if "!PID!" neq "" if "!PID!" neq "0" (
        echo %YELLOW%Stopping process on port 58000 (PID: !PID!)%NC%
        taskkill /PID !PID! /F >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set "stopped_any=true"
        )
    )
)

REM Frontend port (8088)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8088 "') do (
    set "PID=%%a"
    if "!PID!" neq "" if "!PID!" neq "0" (
        echo %YELLOW%Stopping process on port 8088 (PID: !PID!)%NC%
        taskkill /PID !PID! /F >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set "stopped_any=true"
        )
    )
)

REM Stop DocExtract related processes
echo %BLUE%Checking DocExtract related processes...%NC%

REM Stop uvicorn processes
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" ^| findstr python') do (
    set "PID=%%a"
    REM Check if this python process is running uvicorn with main:app
    wmic process where "ProcessId=!PID!" get CommandLine /format:list 2>nul | findstr /I "uvicorn.*main:app" >nul
    if !ERRORLEVEL! equ 0 (
        echo %YELLOW%Stopping uvicorn process (PID: !PID!)%NC%
        taskkill /PID !PID! /F >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set "stopped_any=true"
        )
    )
)

REM Stop npm/node processes
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" ^| findstr node') do (
    set "PID=%%a"
    REM Check if this node process is running npm start or react-scripts
    wmic process where "ProcessId=!PID!" get CommandLine /format:list 2>nul | findstr /I "npm.*start\|react-scripts" >nul
    if !ERRORLEVEL! equ 0 (
        echo %YELLOW%Stopping npm/node process (PID: !PID!)%NC%
        taskkill /PID !PID! /F >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            set "stopped_any=true"
        )
    )
)

REM Clean up log files option
if exist "%PROJECT_ROOT%\backend.log" (
    set /p "DELETE_LOGS=Delete log files? (y/N): "
    if /i "!DELETE_LOGS!"=="y" (
        del "%PROJECT_ROOT%\backend.log" >nul 2>&1
        del "%PROJECT_ROOT%\frontend.log" >nul 2>&1
        echo %GREEN%Log files deleted%NC%
    )
)

REM Clean up PID directory
if exist "%PID_DIR%" (
    rmdir "%PID_DIR%" >nul 2>&1
)

echo.
if "%stopped_any%"=="true" (
    echo %GREEN%DocExtract system stopped successfully%NC%
) else (
    echo %BLUE%No running DocExtract processes found%NC%
)

REM Check port status
echo.
echo %BLUE%Port Status Check:%NC%
netstat -an | findstr ":58000 " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%WARNING: Port 58000 still in use%NC%
    netstat -an | findstr ":58000 "
) else (
    echo %GREEN%Port 58000 available%NC%
)

netstat -an | findstr ":8088 " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%WARNING: Port 8088 still in use%NC%
    netstat -an | findstr ":8088 "
) else (
    echo %GREEN%Port 8088 available%NC%
)

echo.
pause