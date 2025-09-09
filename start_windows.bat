@echo off
echo 🚀 DocExtract Backend 시작 (Windows)

REM 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true
set HOST=0.0.0.0
set PORT=58000
set CONDA_ENV=DocExtract

echo 📁 백엔드 디렉토리로 이동...
cd /d "%~dp0\backend"

echo 🔄 Conda 환경 활성화...
call conda activate %CONDA_ENV%

echo 🗄️ 데이터 디렉토리 확인/생성...
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads

echo 📦 의존성 설치...
pip install -r requirements.txt

echo 🗄️ 데이터베이스 초기화...
python -c "from db.db import Base, engine; Base.metadata.create_all(bind=engine); print('Database initialized')" 2>nul

echo.
echo 🎯 서버 시작...
echo 📍 서버 주소: http://localhost:%PORT%
echo 📚 API 문서: http://localhost:%PORT%/docs
echo.

REM 서버 실행
uvicorn main:app --reload --host %HOST% --port %PORT%

pause