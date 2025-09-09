@echo off
REM DocExtract Backend 실행 스크립트 - 색상 코드 비활성화 버전

REM 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

REM uvicorn 색상 출력 비활성화
set NO_COLOR=1
set FORCE_COLOR=0

REM Python 버퍼링 비활성화 (실시간 출력)
set PYTHONUNBUFFERED=1

REM 백엔드 디렉토리로 이동
cd /d "C:\Servers\cm11_mc\Tagdstiller\backend"

REM Conda 환경 활성화
call conda activate DocExtract

REM 서버 실행 (색상 없이)
uvicorn main:app --reload --host 0.0.0.0 --port 58000 --no-use-colors