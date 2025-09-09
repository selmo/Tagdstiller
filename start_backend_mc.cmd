@echo off
REM DocExtract Backend 실행 스크립트 (MC_DOC용)
REM 수정된 버전 - 환경 설정 및 오류 처리 포함

echo 🚀 DocExtract Backend 시작 (MC_DOC)

REM 오프라인 모드 환경변수 설정 (Windows 초기화 문제 해결)
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

REM 서버 설정
set HOST=0.0.0.0
set PORT=58000
set CONDA_ENV=DocExtract

echo 📍 서버 설정: %HOST%:%PORT%
echo 🔄 Conda 환경: %CONDA_ENV%
echo 🔄 오프라인 모드: %OFFLINE_MODE%

REM 백엔드 디렉토리로 이동
set BACKEND_DIR=C:\Servers\cm11_mc\Tagdstiller\backend
echo 📁 백엔드 디렉토리: %BACKEND_DIR%

if not exist "%BACKEND_DIR%" (
    echo ❌ 오류: 백엔드 디렉토리를 찾을 수 없습니다: %BACKEND_DIR%
    pause
    exit /b 1
)

cd /d "%BACKEND_DIR%"

REM main.py 파일 확인
if not exist "main.py" (
    echo ❌ 오류: main.py 파일이 없습니다
    echo 현재 위치: %CD%
    pause
    exit /b 1
)

REM Conda 환경 활성화
echo 🔄 Conda 환경 활성화 중...
call conda activate %CONDA_ENV%
if errorlevel 1 (
    echo ❌ 오류: Conda 환경 활성화 실패
    echo DocExtract Conda 환경이 생성되어 있는지 확인하세요
    pause
    exit /b 1
)

REM Python/uvicorn 확인
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 오류: Python을 찾을 수 없습니다
    pause
    exit /b 1
)

uvicorn --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️ uvicorn 설치 확인 중...
    pip install uvicorn
)

echo.
echo 🎯 DocExtract 백엔드 서버 시작
echo 📍 서버 주소: http://localhost:%PORT%
echo 📚 API 문서: http://localhost:%PORT%/docs
echo 🛠️ 대체 문서: http://localhost:%PORT%/redoc  
echo.
echo 서버를 중지하려면 Ctrl+C를 누르세요
echo.

REM 서버 실행
uvicorn main:app --reload --host %HOST% --port %PORT%

REM 서버 시작 대기 및 상태 확인
timeout /t 3 >nul
echo 🔍 서버 상태 확인 중...

:end
echo.
echo ✅ 백엔드 서버가 별도 창에서 실행 중입니다
echo 📝 서버를 중지하려면 해당 창을 닫으세요
pause