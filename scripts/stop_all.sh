#!/bin/bash

# DocExtract 시스템 중지 스크립트
# 사용법: ./scripts/stop_all.sh

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}🛑 DocExtract 시스템 중지${NC}"
echo ""

# 스크립트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.pids"

echo -e "${BLUE}📁 프로젝트 루트: $PROJECT_ROOT${NC}"

# PID 파일들로 프로세스 종료
stopped_any=false

# 백엔드 프로세스 종료
if [[ -f "$PID_DIR/backend.pid" ]]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}🔧 백엔드 서버 종료 중... (PID: $BACKEND_PID)${NC}"
        kill $BACKEND_PID
        
        # graceful shutdown 대기
        for i in {1..10}; do
            if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 강제 종료가 필요한 경우
        if ps -p $BACKEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}강제 종료 중...${NC}"
            kill -9 $BACKEND_PID 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ 백엔드 서버 종료 완료${NC}"
        stopped_any=true
    else
        echo -e "${YELLOW}⚠️ 백엔드 프로세스가 이미 종료되었습니다 (PID: $BACKEND_PID)${NC}"
    fi
    rm -f "$PID_DIR/backend.pid"
fi

# 프론트엔드 프로세스 종료
if [[ -f "$PID_DIR/frontend.pid" ]]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -e "${YELLOW}🎨 프론트엔드 서버 종료 중... (PID: $FRONTEND_PID)${NC}"
        kill $FRONTEND_PID
        
        # graceful shutdown 대기
        for i in {1..10}; do
            if ! ps -p $FRONTEND_PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # 강제 종료가 필요한 경우
        if ps -p $FRONTEND_PID > /dev/null 2>&1; then
            echo -e "${YELLOW}강제 종료 중...${NC}"
            kill -9 $FRONTEND_PID 2>/dev/null || true
        fi
        
        echo -e "${GREEN}✅ 프론트엔드 서버 종료 완료${NC}"
        stopped_any=true
    else
        echo -e "${YELLOW}⚠️ 프론트엔드 프로세스가 이미 종료되었습니다 (PID: $FRONTEND_PID)${NC}"
    fi
    rm -f "$PID_DIR/frontend.pid"
fi

# 포트별로 프로세스 찾아서 종료 (백업)
echo -e "${BLUE}🔍 포트별 프로세스 확인 중...${NC}"

# 백엔드 포트 (58000) 확인
BACKEND_PORT_PID=$(lsof -ti :58000 2>/dev/null || true)
if [[ -n "$BACKEND_PORT_PID" ]]; then
    echo -e "${YELLOW}📍 포트 58000에서 실행 중인 프로세스 종료: $BACKEND_PORT_PID${NC}"
    kill $BACKEND_PORT_PID 2>/dev/null || true
    stopped_any=true
fi

# 프론트엔드 포트 (8088) 확인
FRONTEND_PORT_PID=$(lsof -ti :8088 2>/dev/null || true)
if [[ -n "$FRONTEND_PORT_PID" ]]; then
    echo -e "${YELLOW}📍 포트 8088에서 실행 중인 프로세스 종료: $FRONTEND_PORT_PID${NC}"
    kill $FRONTEND_PORT_PID 2>/dev/null || true
    stopped_any=true
fi

# DocExtract 관련 프로세스 찾아서 종료
echo -e "${BLUE}🔍 DocExtract 관련 프로세스 확인 중...${NC}"

# uvicorn 프로세스 찾기
UVICORN_PIDS=$(pgrep -f "uvicorn.*main:app" 2>/dev/null || true)
if [[ -n "$UVICORN_PIDS" ]]; then
    echo -e "${YELLOW}🔧 Uvicorn 프로세스 종료 중: $UVICORN_PIDS${NC}"
    echo $UVICORN_PIDS | xargs kill 2>/dev/null || true
    stopped_any=true
fi

# npm start 프로세스 찾기
NPM_PIDS=$(pgrep -f "npm.*start" 2>/dev/null || true)
if [[ -n "$NPM_PIDS" ]]; then
    echo -e "${YELLOW}🎨 npm start 프로세스 종료 중: $NPM_PIDS${NC}"
    echo $NPM_PIDS | xargs kill 2>/dev/null || true
    stopped_any=true
fi

# 로그 파일 정리 옵션
if [[ -f "$PROJECT_ROOT/backend.log" ]] || [[ -f "$PROJECT_ROOT/frontend.log" ]]; then
    echo ""
    read -p "로그 파일을 삭제하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f "$PROJECT_ROOT/backend.log"
        rm -f "$PROJECT_ROOT/frontend.log"
        echo -e "${GREEN}✅ 로그 파일 삭제 완료${NC}"
    fi
fi

# PID 디렉토리 정리
if [[ -d "$PID_DIR" ]]; then
    rmdir "$PID_DIR" 2>/dev/null || true
fi

echo ""
if [[ "$stopped_any" == true ]]; then
    echo -e "${GREEN}✅ DocExtract 시스템 종료 완료${NC}"
else
    echo -e "${BLUE}ℹ️ 실행 중인 DocExtract 프로세스가 없습니다${NC}"
fi

# 포트 상태 확인
echo ""
echo -e "${BLUE}📊 포트 상태 확인:${NC}"
if lsof -i :58000 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 포트 58000이 여전히 사용 중입니다${NC}"
    lsof -i :58000
else
    echo -e "${GREEN}✅ 포트 58000 사용 가능${NC}"
fi

if lsof -i :8088 > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 포트 8088이 여전히 사용 중입니다${NC}"
    lsof -i :8088
else
    echo -e "${GREEN}✅ 포트 8088 사용 가능${NC}"
fi