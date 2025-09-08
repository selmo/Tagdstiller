@echo off
REM DocExtract Backend Start Script (Windows)
REM Usage: start_backend.bat [dev|prod]

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
set "HOST=%HOST%"
if "%HOST%"=="" set "HOST=0.0.0.0"
set "PORT=%PORT%"
if "%PORT%"=="" set "PORT=58000"
set "CONDA_ENV=%CONDA_ENV%"
if "%CONDA_ENV%"=="" set "CONDA_ENV=DocExtract"

echo %BLUE%DocExtract Backend Starting%NC%
echo %YELLOW%Mode: %MODE%%NC%
echo %YELLOW%Host: %HOST%%NC%
echo %YELLOW%Port: %PORT%%NC%
echo %YELLOW%Conda Environment: %CONDA_ENV%%NC%
echo.

REM Get project directories
for %%i in ("%~dp0") do set "SCRIPT_DIR=%%~fi"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_ROOT=%%~fi"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

echo %BLUE%Project Root: %PROJECT_ROOT%%NC%
echo %BLUE%Backend Directory: %BACKEND_DIR%%NC%

REM Check backend directory
if not exist "%BACKEND_DIR%" (
    echo %RED%ERROR: backend directory not found%NC%
    echo Expected location: %BACKEND_DIR%
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%"

REM Check main.py file
if not exist "main.py" (
    echo %RED%ERROR: main.py file not found%NC%
    echo Current location: %CD%
    pause
    exit /b 1
)

REM Check conda installation
where conda >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %RED%ERROR: conda is not installed%NC%
    echo Please install Anaconda or Miniconda: https://conda.io/projects/conda/en/latest/user-guide/install/index.html
    pause
    exit /b 1
)

REM Check if conda environment exists
conda info --envs | findstr /B "%CONDA_ENV% " >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo %YELLOW%Creating Conda environment: %CONDA_ENV%%NC%
    conda create -n %CONDA_ENV% python=3.11 -y
    if %ERRORLEVEL% neq 0 (
        echo %RED%ERROR: Failed to create Conda environment%NC%
        pause
        exit /b 1
    )
    echo %GREEN%Conda environment created successfully%NC%
) else (
    echo %GREEN%Conda environment found: %CONDA_ENV%%NC%
)

REM Activate conda environment
echo %YELLOW%Activating Conda environment: %CONDA_ENV%%NC%
call conda activate %CONDA_ENV%
if %ERRORLEVEL% neq 0 (
    echo %RED%ERROR: Failed to activate Conda environment%NC%
    pause
    exit /b 1
)

REM Check dependencies
echo %YELLOW%Checking dependencies...%NC%
if not exist "requirements.txt" (
    echo %RED%ERROR: requirements.txt file not found%NC%
    pause
    exit /b 1
)

REM Upgrade pip
echo %YELLOW%Upgrading pip...%NC%
python -m pip install --upgrade pip >nul 2>&1

REM Install dependencies
echo %YELLOW%Installing dependencies...%NC%
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo %RED%ERROR: Failed to install dependencies%NC%
    pause
    exit /b 1
)
echo %GREEN%Dependencies installed successfully%NC%

REM Create data directory
if not exist "data" (
    echo %YELLOW%Creating data directory...%NC%
    mkdir data\uploads
    echo %GREEN%Data directory created successfully%NC%
)

REM Initialize database
if not exist "data\db.sqlite3" (
    echo %YELLOW%Initializing database...%NC%
    python -c "from main import app; print('Database initialized')" >nul 2>&1
    echo %GREEN%Database initialization complete%NC%
)

REM Check if port is in use
netstat -an | findstr ":%PORT% " >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo %YELLOW%WARNING: Port %PORT% is already in use%NC%
    echo %YELLOW%To use different port: set PORT=8001 ^&^& start_backend.bat%NC%
    set /p "CONFIRM=Continue anyway? (y/N): "
    if /i not "!CONFIRM!"=="y" (
        exit /b 1
    )
)

echo.
echo %GREEN%Starting server...%NC%
echo %BLUE%Server URL: http://localhost:%PORT%%NC%
echo %BLUE%API Documentation: http://localhost:%PORT%/docs%NC%
echo %BLUE%Alternative Docs: http://localhost:%PORT%/redoc%NC%
echo.
echo %YELLOW%Press Ctrl+C to stop the server%NC%
echo.

REM Start server
if "%MODE%"=="prod" (
    echo %GREEN%Starting in production mode%NC%
    uvicorn main:app --host %HOST% --port %PORT%
) else (
    echo %GREEN%Starting in development mode (auto-reload)%NC%
    uvicorn main:app --reload --host %HOST% --port %PORT%
)