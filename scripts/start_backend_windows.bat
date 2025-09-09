@echo off
REM DocExtract Backend 실행 스크립트 (Windows용)
REM 사용법: start_backend_windows.bat [dev|prod]

setlocal enabledelayedexpansion

REM 색상 정의 (Windows에서는 제한적)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "BLUE=[94m"
set "NC=[0m"

REM 기본값 설정
set "MODE=%1"
if "%MODE%"=="" set "MODE=dev"
if "%HOST%"=="" set "HOST=0.0.0.0"
if "%PORT%"=="" set "PORT=58000"
if "%CONDA_ENV%"=="" set "CONDA_ENV=DocExtract"

echo %BLUE%🚀 DocExtract Backend 시작 (Windows)%NC%
echo %YELLOW%모드: %MODE%%NC%
echo %YELLOW%호스트: %HOST%%NC%
echo %YELLOW%포트: %PORT%%NC%
echo %YELLOW%Conda 환경: %CONDA_ENV%%NC%
echo.

REM 프로젝트 루트 디렉토리로 이동
cd /d "%~dp0\.."
set "PROJECT_ROOT=%CD%"
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

echo %BLUE%📁 프로젝트 루트: %PROJECT_ROOT%%NC%
echo %BLUE%📁 백엔드 디렉토리: %BACKEND_DIR%%NC%

REM 백엔드 디렉토리 확인
if not exist "%BACKEND_DIR%" (
    echo %RED%❌ 오류: backend 디렉토리를 찾을 수 없습니다%NC%
    echo 예상 위치: %BACKEND_DIR%
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%"

REM main.py 파일 확인
if not exist "main.py" (
    echo %RED%❌ 오류: main.py 파일을 찾을 수 없습니다%NC%
    echo 현재 위치: %CD%
    pause
    exit /b 1
)

REM Conda 확인
conda --version >nul 2>&1
if errorlevel 1 (
    echo %RED%❌ 오류: conda가 설치되어 있지 않습니다%NC%
    echo Anaconda 또는 Miniconda를 설치해주세요
    pause
    exit /b 1
)

REM Conda 환경 확인 및 생성
conda info --envs | findstr "%CONDA_ENV%" >nul
if errorlevel 1 (
    echo %YELLOW%📦 Conda 환경 생성 중: %CONDA_ENV%%NC%
    conda create -n %CONDA_ENV% python=3.11 -y
    echo %GREEN%✅ Conda 환경 생성 완료%NC%
) else (
    echo %GREEN%✅ Conda 환경 확인: %CONDA_ENV%%NC%
)

REM Conda 환경 활성화
echo %YELLOW%🔄 Conda 환경 활성화 중: %CONDA_ENV%%NC%
call conda activate %CONDA_ENV%

REM 의존성 설치 확인
echo %YELLOW%📋 의존성 확인 중...%NC%
if not exist "requirements.txt" (
    echo %RED%❌ requirements.txt 파일이 없습니다%NC%
    pause
    exit /b 1
)

REM pip 업그레이드
echo %YELLOW%🔄 pip 업그레이드 중...%NC%
pip install --upgrade pip >nul 2>&1

REM 의존성 설치
echo %YELLOW%📦 의존성 설치 중...%NC%
pip install -r requirements.txt
echo %GREEN%✅ 의존성 설치 완료%NC%

REM 데이터 디렉토리 생성
if not exist "data" (
    echo %YELLOW%📁 데이터 디렉토리 생성 중...%NC%
    mkdir data\uploads
    echo %GREEN%✅ 데이터 디렉토리 생성 완료%NC%
)

REM 오프라인 모드로 데이터베이스 초기화 (Windows 문제 해결)
if not exist "data\db.sqlite3" (
    echo %YELLOW%🗄️ 데이터베이스 초기화 중 (오프라인 모드)...%NC%
    set OFFLINE_MODE=true
    set SKIP_EXTERNAL_CHECKS=true
    python -c "import os; os.environ['OFFLINE_MODE']='true'; os.environ['SKIP_EXTERNAL_CHECKS']='true'; from main import app; print('Database initialized')" >nul 2>&1
    if errorlevel 1 (
        echo %RED%❌ 데이터베이스 초기화 실패%NC%
        echo %YELLOW%수동으로 초기화를 시도합니다...%NC%
        python -c "from db.db import Base, engine; Base.metadata.create_all(bind=engine); print('Manual DB init complete')"
    )
    echo %GREEN%✅ 데이터베이스 초기화 완료%NC%
)

REM 포트 사용 중인지 확인 (Windows용)
netstat -an | findstr ":%PORT%" >nul
if not errorlevel 1 (
    echo %YELLOW%⚠️ 포트 %PORT%이 이미 사용 중입니다%NC%
    echo %YELLOW%다른 포트를 사용하려면: set PORT=8001 ^& start_backend_windows.bat%NC%
    set /p REPLY="계속하시겠습니까? (y/N): "
    if /i not "!REPLY!"=="y" exit /b 1
)

echo.
echo %GREEN%🎯 서버 시작 중...%NC%
echo %BLUE%📍 서버 주소: http://localhost:%PORT%%NC%
echo %BLUE%📚 API 문서: http://localhost:%PORT%/docs%NC%
echo %BLUE%🛠️ 대체 문서: http://localhost:%PORT%/redoc%NC%
echo.
echo %YELLOW%서버를 중지하려면 Ctrl+C를 누르세요%NC%
echo.

REM 오프라인 모드 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

REM 서버 실행
if "%MODE%"=="prod" (
    echo %GREEN%🏭 프로덕션 모드로 시작%NC%
    uvicorn main:app --host %HOST% --port %PORT%
) else (
    echo %GREEN%🔧 개발 모드로 시작 (자동 리로드)%NC%
    uvicorn main:app --reload --host %HOST% --port %PORT%
)

pause