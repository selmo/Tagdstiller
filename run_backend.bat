@echo off
:: DocExtract Backend 실행 - 가장 간단한 버전

:: 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

:: 디렉토리 이동
cd /d "C:\Servers\cm11_mc\Tagdstiller\backend"

:: Conda 환경 활성화 및 서버 실행
call conda activate DocExtract && uvicorn main:app --reload --host 0.0.0.0 --port 58000