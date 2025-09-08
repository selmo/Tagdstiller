@echo off
REM DocExtract System Status Check Script (Windows)
REM Usage: status.bat

setlocal enabledelayedexpansion

REM Color definitions (Windows compatible)
set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "PURPLE=[95m"
set "NC=[0m"

echo %PURPLE%DocExtract System Status%NC%
echo.

REM Get project directories
for %%i in ("%~dp0") do set "SCRIPT_DIR=%%~fi"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"
set "PID_DIR=%PROJECT_ROOT%\.pids"

echo %BLUE%Project Root: %PROJECT_ROOT%%NC%
echo.

REM Check running processes
echo %BLUE%Process Status:%NC%

set "BACKEND_STATUS=stopped"
set "FRONTEND_STATUS=stopped"

REM Check backend processes
tasklist /FI "WINDOWTITLE eq DocExtract Backend*" 2>nul | findstr /I cmd >nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%Backend: Running (Window Process)%NC%
    set "BACKEND_STATUS=running"
) else (
    REM Check for uvicorn processes
    set "UVICORN_FOUND=false"
    for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| findstr python') do (
        set "PID=%%a"
        wmic process where "ProcessId=!PID!" get CommandLine /format:list 2>nul | findstr /I "uvicorn.*main:app" >nul
        if !ERRORLEVEL! equ 0 (
            echo %GREEN%Backend: Running (PID: !PID!)%NC%
            set "BACKEND_STATUS=running"
            set "UVICORN_FOUND=true"
        )
    )
    if "!UVICORN_FOUND!"=="false" (
        echo %YELLOW%Backend: Not running%NC%
    )
)

REM Check frontend processes
tasklist /FI "WINDOWTITLE eq DocExtract Frontend*" 2>nul | findstr /I cmd >nul
if %ERRORLEVEL% equ 0 (
    echo %GREEN%Frontend: Running (Window Process)%NC%
    set "FRONTEND_STATUS=running"
) else (
    REM Check for npm/node processes
    set "NODE_FOUND=false"
    for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" 2^>nul ^| findstr node') do (
        set "PID=%%a"
        wmic process where "ProcessId=!PID!" get CommandLine /format:list 2>nul | findstr /I "npm.*start\|react-scripts" >nul
        if !ERRORLEVEL! equ 0 (
            echo %GREEN%Frontend: Running (PID: !PID!)%NC%
            set "FRONTEND_STATUS=running"
            set "NODE_FOUND=true"
        )
    )
    if "!NODE_FOUND!"=="false" (
        echo %YELLOW%Frontend: Not running%NC%
    )
)

echo.

REM Port status check
echo %BLUE%Port Status:%NC%

REM Backend port (58000)
netstat -an | findstr ":58000 " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":58000 "') do (
        set "PID=%%a"
        echo %GREEN%Port 58000: In use (PID: !PID!)%NC%
    )
    
    REM API response check
    curl -s http://localhost:58000/ >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo %GREEN%  API Response: OK%NC%
    ) else (
        echo %RED%  API Response: Failed%NC%
    )
) else (
    echo %YELLOW%Port 58000: Not in use%NC%
)

REM Frontend port (8088)
netstat -an | findstr ":8088 " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8088 "') do (
        set "PID=%%a"
        echo %GREEN%Port 8088: In use (PID: !PID!)%NC%
    )
    
    REM Web server response check
    curl -s http://localhost:8088/ >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo %GREEN%  Web Server Response: OK%NC%
    ) else (
        echo %RED%  Web Server Response: Failed%NC%
    )
) else (
    echo %YELLOW%Port 8088: Not in use%NC%
)

echo.

REM Related processes
echo %BLUE%Related Processes:%NC%

REM Uvicorn processes
set "UVICORN_COUNT=0"
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| findstr python') do (
    set "PID=%%a"
    wmic process where "ProcessId=!PID!" get CommandLine /format:list 2>nul | findstr /I "uvicorn.*main:app" >nul
    if !ERRORLEVEL! equ 0 (
        echo %GREEN%  Uvicorn Process: PID !PID!%NC%
        set /a UVICORN_COUNT+=1
    )
)
if %UVICORN_COUNT% equ 0 (
    echo %YELLOW%  No Uvicorn processes found%NC%
)

REM npm/node processes
set "NODE_COUNT=0"
for /f "tokens=2" %%a in ('tasklist /FI "IMAGENAME eq node.exe" 2^>nul ^| findstr node') do (
    set "PID=%%a"
    wmic process where "ProcessId=!PID!" get CommandLine /format:list 2>nul | findstr /I "npm.*start\|react-scripts" >nul
    if !ERRORLEVEL! equ 0 (
        echo %GREEN%  npm/React Process: PID !PID!%NC%
        set /a NODE_COUNT+=1
    )
)
if %NODE_COUNT% equ 0 (
    echo %YELLOW%  No npm/React processes found%NC%
)

echo.

REM Log file status
echo %BLUE%Log File Status:%NC%

if exist "%PROJECT_ROOT%\backend.log" (
    for %%A in ("%PROJECT_ROOT%\backend.log") do set "BACKEND_LOG_SIZE=%%~zA"
    set /a BACKEND_LOG_MB=!BACKEND_LOG_SIZE!/1024/1024
    if !BACKEND_LOG_MB! equ 0 (
        set /a BACKEND_LOG_KB=!BACKEND_LOG_SIZE!/1024
        echo %GREEN%Backend Log: !BACKEND_LOG_KB! KB%NC%
    ) else (
        echo %GREEN%Backend Log: !BACKEND_LOG_MB! MB%NC%
    )
    echo %YELLOW%  Path: %PROJECT_ROOT%\backend.log%NC%
) else (
    echo %YELLOW%Backend Log: Not found%NC%
)

if exist "%PROJECT_ROOT%\frontend.log" (
    for %%A in ("%PROJECT_ROOT%\frontend.log") do set "FRONTEND_LOG_SIZE=%%~zA"
    set /a FRONTEND_LOG_MB=!FRONTEND_LOG_SIZE!/1024/1024
    if !FRONTEND_LOG_MB! equ 0 (
        set /a FRONTEND_LOG_KB=!FRONTEND_LOG_SIZE!/1024
        echo %GREEN%Frontend Log: !FRONTEND_LOG_KB! KB%NC%
    ) else (
        echo %GREEN%Frontend Log: !FRONTEND_LOG_MB! MB%NC%
    )
    echo %YELLOW%  Path: %PROJECT_ROOT%\frontend.log%NC%
) else (
    echo %YELLOW%Frontend Log: Not found%NC%
)

echo.

REM Database status
echo %BLUE%Database Status:%NC%

set "DB_PATH=%PROJECT_ROOT%\backend\data\db.sqlite3"
if exist "%DB_PATH%" (
    for %%A in ("%DB_PATH%") do set "DB_SIZE=%%~zA"
    set /a DB_MB=!DB_SIZE!/1024/1024
    if !DB_MB! equ 0 (
        set /a DB_KB=!DB_SIZE!/1024
        echo %GREEN%SQLite Database: !DB_KB! KB%NC%
    ) else (
        echo %GREEN%SQLite Database: !DB_MB! MB%NC%
    )
    echo %YELLOW%  Path: %DB_PATH%%NC%
) else (
    echo %YELLOW%Database file not found%NC%
)

REM Upload directory status
set "UPLOAD_DIR=%PROJECT_ROOT%\backend\data\uploads"
if exist "%UPLOAD_DIR%" (
    set "UPLOAD_COUNT=0"
    for /r "%UPLOAD_DIR%" %%F in (*) do set /a UPLOAD_COUNT+=1
    if !UPLOAD_COUNT! gtr 0 (
        echo %GREEN%Upload Files: !UPLOAD_COUNT! files%NC%
    ) else (
        echo %YELLOW%Upload Files: None%NC%
    )
    echo %YELLOW%  Path: %UPLOAD_DIR%%NC%
) else (
    echo %YELLOW%Upload directory not found%NC%
)

echo.

REM Overall status summary
echo %PURPLE%Overall Status Summary:%NC%

if "%BACKEND_STATUS%"=="running" if "%FRONTEND_STATUS%"=="running" (
    echo %GREEN%System Status: Running normally%NC%
    echo %BLUE%Access URLs:%NC%
    echo %GREEN%  Web Application: http://localhost:8088%NC%
    echo %GREEN%  API Server: http://localhost:58000%NC%
    echo %GREEN%  API Documentation: http://localhost:58000/docs%NC%
) else if "%BACKEND_STATUS%"=="running" (
    echo %YELLOW%System Status: Backend only%NC%
) else if "%FRONTEND_STATUS%"=="running" (
    echo %YELLOW%System Status: Frontend only%NC%
) else (
    echo %RED%System Status: Stopped%NC%
    echo %BLUE%To start: start_all.bat%NC%
)

echo.
pause