@echo off
REM DocExtract Frontend Start Script (Windows)
REM Usage: start_frontend.bat [dev|build|test]

setlocal enabledelayedexpansion

REM Error handling
if "%ERRORLEVEL%" neq "0" exit /b %ERRORLEVEL%

REM Color definitions (Windows compatible)
set "BLUE=[94m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"

REM Default values
set "MODE=%1"
if "%MODE%"=="" set "MODE=dev"
set "PORT=%PORT%"
if "%PORT%"=="" set "PORT=8088"

echo %BLUE%DocExtract Frontend Starting%NC%
echo %YELLOW%Mode: %MODE%%NC%
echo %YELLOW%Port: %PORT%%NC%
echo.

REM Get project directories
for %%i in ("%~dp0") do set "SCRIPT_DIR=%%~fi"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"
set "FRONTEND_DIR=%PROJECT_ROOT%\frontend"

echo %BLUE%Project Root: %PROJECT_ROOT%%NC%
echo %BLUE%Frontend Directory: %FRONTEND_DIR%%NC%

REM Check frontend directory
if not exist "%FRONTEND_DIR%" (
    echo %RED%ERROR: frontend directory not found%NC%
    echo Expected location: %FRONTEND_DIR%
    pause
    exit /b 1
)

cd /d "%FRONTEND_DIR%"

REM Check package.json file
if not exist "package.json" (
    echo %RED%ERROR: package.json file not found%NC%
    echo Current location: %CD%
    pause
    exit /b 1
)

REM Check Node.js installation
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%ERROR: Node.js is not installed%NC%
    echo Please install Node.js: https://nodejs.org/
    pause
    exit /b 1
)

REM Check npm installation
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%ERROR: npm is not installed%NC%
    pause
    exit /b 1
)

REM Display versions
for /f "tokens=*" %%a in ('node --version') do set "NODE_VERSION=%%a"
for /f "tokens=*" %%a in ('npm --version') do set "NPM_VERSION=%%a"
echo %GREEN%Node.js: %NODE_VERSION%%NC%
echo %GREEN%npm: %NPM_VERSION%%NC%

REM Check dependencies installation
if not exist "node_modules" (
    echo %YELLOW%Installing dependencies...%NC%
    npm install
    if %ERRORLEVEL% neq 0 (
        echo %RED%ERROR: Failed to install dependencies%NC%
        pause
        exit /b 1
    )
    echo %GREEN%Dependencies installed successfully%NC%
) else (
    echo %YELLOW%Checking dependencies...%NC%
    REM Check if package-lock.json is newer than node_modules
    for %%f in (package-lock.json) do set "LOCK_TIME=%%~tf"
    for %%f in (node_modules) do set "MODULES_TIME=%%~tf"
    
    REM Simple timestamp comparison (this is approximate)
    if exist "package-lock.json" (
        echo %YELLOW%Updating dependencies...%NC%
        npm install
        if %ERRORLEVEL% neq 0 (
            echo %RED%ERROR: Failed to update dependencies%NC%
            pause
            exit /b 1
        )
        echo %GREEN%Dependencies updated successfully%NC%
    ) else (
        echo %GREEN%Dependencies are up to date%NC%
    )
)

REM Check environment variables file
if not exist ".env" if not exist ".env.local" (
    echo %YELLOW%Creating environment variables file...%NC%
    (
        echo # Backend API URL
        echo REACT_APP_API_BASE_URL=http://localhost:58000
        echo.
        echo # Development settings
        echo REACT_APP_ENV=development
    ) > .env.local
    echo %GREEN%.env.local file created successfully%NC%
)

REM Check if port is in use
netstat -an | findstr ":%PORT% " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%WARNING: Port %PORT% is already in use%NC%
    echo %YELLOW%To use different port: set PORT=3001 ^&^& start_frontend.bat%NC%
    set /p "CONFIRM=Continue anyway? (y/N): "
    if /i not "!CONFIRM!"=="y" (
        exit /b 1
    )
)

echo.
echo %GREEN%Starting frontend...%NC%

REM Execute based on mode
if "%MODE%"=="dev" (
    echo %GREEN%Starting in development mode (Hot Reload)%NC%
    echo %BLUE%Development Server: http://localhost:%PORT%%NC%
    echo.
    echo %YELLOW%Press Ctrl+C to stop the server%NC%
    echo.
    set PORT=%PORT%
    npm start
) else if "%MODE%"=="build" (
    echo %GREEN%Building for production...%NC%
    npm run build
    if %ERRORLEVEL% neq 0 (
        echo %RED%ERROR: Build failed%NC%
        pause
        exit /b 1
    )
    echo %GREEN%Build completed successfully%NC%
    echo %BLUE%Build files: %CD%\build%NC%
    
    REM Ask if user wants to serve the build
    set /p "SERVE_BUILD=Serve the built files locally? (y/N): "
    if /i "!SERVE_BUILD!"=="y" (
        where serve >nul 2>&1
        if %ERRORLEVEL% equ 0 (
            echo %GREEN%Starting static file server%NC%
            echo %BLUE%Server URL: http://localhost:%PORT%%NC%
            serve -s build -l %PORT%
        ) else (
            echo %YELLOW%'serve' package not installed%NC%
            echo %YELLOW%Install: npm install -g serve%NC%
            echo %YELLOW%Manual run: npx serve -s build -l %PORT%%NC%
        )
    )
) else if "%MODE%"=="test" (
    echo %GREEN%Running tests%NC%
    npm test
) else (
    echo %RED%ERROR: Unknown mode: %MODE%%NC%
    echo Available modes: dev, build, test
    pause
    exit /b 1
)