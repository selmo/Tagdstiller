@echo off
REM DocExtract Backend 실행 스크립트 (MC_DOC용) - 공백 처리 개선
REM 단순화된 버전 - 즉시 실행

REM 환경변수 설정
set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

REM 백엔드 디렉토리로 이동 (따옴표로 경로 보호)
cd /d "C:\Servers\cm11_mc\Tagdstiller\backend"

REM Conda 환경 활성화
call conda activate DocExtract

REM 서버 실행 (한 줄로 실행)
start "MC_DOC" uvicorn main:app --reload --host 0.0.0.0 --port 58000