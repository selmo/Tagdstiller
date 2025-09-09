@echo off
REM 원본 명령어 수정 버전 (오타 수정 및 환경변수 추가)

set OFFLINE_MODE=true
set SKIP_EXTERNAL_CHECKS=true

REM uvicorn 오타 수정 및 Conda 환경 포함
start "MC_DOC" cmd /k "cd /d C:\Servers\cm11_mc\Tagdstiller\backend && conda activate DocExtract && uvicorn main:app --reload --host 0.0.0.0 --port 58000"