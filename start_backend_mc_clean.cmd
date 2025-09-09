@echo off
REM DocExtract Backend 실행 - 깔끔한 출력 버전

REM 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true
set PYTHONUNBUFFERED=1

REM Windows Terminal ANSI 지원 활성화 (Windows 10+)
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

REM 백엔드 디렉토리로 이동
cd /d "C:\Servers\cm11_mc\Tagdstiller\backend"

REM Conda 환경 활성화
call conda activate DocExtract

echo ========================================
echo   DocExtract Backend Server
echo   http://localhost:58000
echo   API Docs: http://localhost:58000/docs
echo ========================================
echo.

REM 서버 실행 (커스텀 로그 설정 사용)
uvicorn main:app --reload --host 0.0.0.0 --port 58000 --log-config uvicorn_config.py