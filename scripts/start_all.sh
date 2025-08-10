#!/bin/bash

# DocExtract 전체 시스템 실행 스크립트
# 사용법: ./scripts/start_all.sh [dev|prod]

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 기본값 설정
MODE=${1:-dev}
CONDA_ENV=${CONDA_ENV:-"DocExtract"}

echo -e "${PURPLE}🚀 DocExtract 전체 시스템 시작${NC}"
echo -e "${YELLOW}모드: $MODE${NC}"
echo -e "${YELLOW}Conda 환경: $CONDA_ENV${NC}"
echo ""

# 스크립트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}📁 프로젝트 루트: $PROJECT_ROOT${NC}"

# 스크립트 파일 확인
BACKEND_SCRIPT="$SCRIPT_DIR/start_backend.sh"
FRONTEND_SCRIPT="$SCRIPT_DIR/start_frontend.sh"

if [[ ! -f "$BACKEND_SCRIPT" ]]; then
    echo -e "${RED}❌ 백엔드 스크립트를 찾을 수 없습니다: $BACKEND_SCRIPT${NC}"
    exit 1
fi

if [[ ! -f "$FRONTEND_SCRIPT" ]]; then
    echo -e "${RED}❌ 프론트엔드 스크립트를 찾을 수 없습니다: $FRONTEND_SCRIPT${NC}"
    exit 1
fi

# 스크립트 실행 권한 확인 및 부여
if [[ ! -x "$BACKEND_SCRIPT" ]]; then
    chmod +x "$BACKEND_SCRIPT"
fi

if [[ ! -x "$FRONTEND_SCRIPT" ]]; then
    chmod +x "$FRONTEND_SCRIPT"
fi

# PID 파일 디렉토리 생성
PID_DIR="$PROJECT_ROOT/.pids"
mkdir -p "$PID_DIR"

# 기존 프로세스 정리 함수
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 시스템 종료 중...${NC}"
    
    # PID 파일들 확인하고 프로세스 종료
    if [[ -f "$PID_DIR/backend.pid" ]]; then
        BACKEND_PID=$(cat "$PID_DIR/backend.pid")
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}🔧 백엔드 서버 종료 중... (PID: $BACKEND_PID)${NC}"
            kill $BACKEND_PID
            wait $BACKEND_PID 2>/dev/null || true
        fi
        rm -f "$PID_DIR/backend.pid"
    fi
    
    if [[ -f "$PID_DIR/frontend.pid" ]]; then
        FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}🎨 프론트엔드 서버 종료 중... (PID: $FRONTEND_PID)${NC}"
            kill $FRONTEND_PID
            wait $FRONTEND_PID 2>/dev/null || true
        fi
        rm -f "$PID_DIR/frontend.pid"
    fi
    
    echo -e "${GREEN}✅ 시스템 종료 완료${NC}"
    exit 0
}

# Ctrl+C 시 cleanup 함수 실행
trap cleanup SIGINT SIGTERM

# 포트 충돌 확인
BACKEND_PORT=${BACKEND_PORT:-58000}
FRONTEND_PORT=${FRONTEND_PORT:-8080}

echo -e "${YELLOW}🔍 포트 사용 상태 확인 중...${NC}"

if lsof -i :$BACKEND_PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 백엔드 포트 $BACKEND_PORT이 이미 사용 중입니다${NC}"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 프론트엔드 포트 $FRONTEND_PORT이 이미 사용 중입니다${NC}"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎯 서버들을 순차적으로 시작합니다...${NC}"
echo ""

# 백엔드 시작
echo -e "${BLUE}1️⃣ 백엔드 서버 시작 중...${NC}"
CONDA_ENV=$CONDA_ENV "$BACKEND_SCRIPT" $MODE > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$PID_DIR/backend.pid"

# 백엔드 시작 대기
echo -e "${YELLOW}⏳ 백엔드 서버 시작 대기 중...${NC}"
sleep 5

# 백엔드 상태 확인
if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "${RED}❌ 백엔드 서버 시작 실패${NC}"
    echo -e "${YELLOW}로그 확인: tail -f $PROJECT_ROOT/backend.log${NC}"
    exit 1
fi

# 백엔드 API 응답 확인
for i in {1..10}; do
    if curl -s http://localhost:$BACKEND_PORT/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 백엔드 서버 시작 완료 (PID: $BACKEND_PID)${NC}"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo -e "${RED}❌ 백엔드 서버 응답 없음${NC}"
        cleanup
        exit 1
    fi
    sleep 2
done

sleep 2

# 프론트엔드 시작
echo -e "${BLUE}2️⃣ 프론트엔드 서버 시작 중...${NC}"
"$FRONTEND_SCRIPT" $MODE > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"

# 프론트엔드 시작 대기
echo -e "${YELLOW}⏳ 프론트엔드 서버 시작 대기 중...${NC}"
sleep 8

# 프론트엔드 상태 확인
if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo -e "${RED}❌ 프론트엔드 서버 시작 실패${NC}"
    echo -e "${YELLOW}로그 확인: tail -f $PROJECT_ROOT/frontend.log${NC}"
    cleanup
    exit 1
fi

echo -e "${GREEN}✅ 프론트엔드 서버 시작 완료 (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${PURPLE}🎉 DocExtract 시스템이 성공적으로 시작되었습니다!${NC}"
echo ""
echo -e "${BLUE}📍 서비스 정보:${NC}"
echo -e "${GREEN}  🔧 백엔드 API: http://localhost:$BACKEND_PORT${NC}"
echo -e "${GREEN}  📚 API 문서: http://localhost:$BACKEND_PORT/docs${NC}"
echo -e "${GREEN}  🎨 프론트엔드: http://localhost:$FRONTEND_PORT${NC}"
echo ""
echo -e "${BLUE}📋 로그 파일:${NC}"
echo -e "${YELLOW}  백엔드: tail -f $PROJECT_ROOT/backend.log${NC}"
echo -e "${YELLOW}  프론트엔드: tail -f $PROJECT_ROOT/frontend.log${NC}"
echo ""
echo -e "${BLUE}📊 프로세스 정보:${NC}"
echo -e "${YELLOW}  백엔드 PID: $BACKEND_PID${NC}"
echo -e "${YELLOW}  프론트엔드 PID: $FRONTEND_PID${NC}"
echo ""
echo -e "${RED}🛑 시스템을 종료하려면 Ctrl+C를 누르세요${NC}"

# 프로세스들이 종료될 때까지 대기
wait