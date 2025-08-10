#!/bin/bash

# DocExtract 시스템 상태 확인 스크립트
# 사용법: ./scripts/status.sh

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${PURPLE}📊 DocExtract 시스템 상태${NC}"
echo ""

# 스크립트 디렉토리 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_ROOT/.pids"

echo -e "${BLUE}📁 프로젝트 루트: $PROJECT_ROOT${NC}"
echo ""

# PID 파일 확인
echo -e "${BLUE}🔍 PID 파일 상태:${NC}"

if [[ -f "$PID_DIR/backend.pid" ]]; then
    BACKEND_PID=$(cat "$PID_DIR/backend.pid")
    if ps -p $BACKEND_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 백엔드: 실행 중 (PID: $BACKEND_PID)${NC}"
        BACKEND_STATUS="running"
    else
        echo -e "${RED}❌ 백엔드: PID 파일 존재하나 프로세스 없음 (PID: $BACKEND_PID)${NC}"
        BACKEND_STATUS="dead"
    fi
else
    echo -e "${YELLOW}⚠️ 백엔드: PID 파일 없음${NC}"
    BACKEND_STATUS="stopped"
fi

if [[ -f "$PID_DIR/frontend.pid" ]]; then
    FRONTEND_PID=$(cat "$PID_DIR/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 프론트엔드: 실행 중 (PID: $FRONTEND_PID)${NC}"
        FRONTEND_STATUS="running"
    else
        echo -e "${RED}❌ 프론트엔드: PID 파일 존재하나 프로세스 없음 (PID: $FRONTEND_PID)${NC}"
        FRONTEND_STATUS="dead"
    fi
else
    echo -e "${YELLOW}⚠️ 프론트엔드: PID 파일 없음${NC}"
    FRONTEND_STATUS="stopped"
fi

echo ""

# 포트 상태 확인
echo -e "${BLUE}🌐 포트 상태:${NC}"

# 백엔드 포트 (58000)
if lsof -i :58000 > /dev/null 2>&1; then
    PORT_58000_PID=$(lsof -ti :58000)
    echo -e "${GREEN}✅ 포트 58000: 사용 중 (PID: $PORT_58000_PID)${NC}"
    
    # API 응답 확인
    if curl -s http://localhost:58000/ > /dev/null 2>&1; then
        echo -e "${GREEN}  📡 API 응답: 정상${NC}"
    else
        echo -e "${RED}  📡 API 응답: 실패${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ 포트 58000: 사용 안함${NC}"
fi

# 프론트엔드 포트 (8080)
if lsof -i :8080 > /dev/null 2>&1; then
    PORT_8080_PID=$(lsof -ti :8080)
    echo -e "${GREEN}✅ 포트 8080: 사용 중 (PID: $PORT_8080_PID)${NC}"
    
    # 웹 서버 응답 확인
    if curl -s http://localhost:8080/ > /dev/null 2>&1; then
        echo -e "${GREEN}  🌐 웹 서버 응답: 정상${NC}"
    else
        echo -e "${RED}  🌐 웹 서버 응답: 실패${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ 포트 8080: 사용 안함${NC}"
fi

echo ""

# 관련 프로세스 확인
echo -e "${BLUE}⚙️ 관련 프로세스:${NC}"

# Uvicorn 프로세스
UVICORN_PROCESSES=$(pgrep -f "uvicorn.*main:app" 2>/dev/null || true)
if [[ -n "$UVICORN_PROCESSES" ]]; then
    echo -e "${GREEN}✅ Uvicorn 프로세스:${NC}"
    echo "$UVICORN_PROCESSES" | while read pid; do
        echo -e "${YELLOW}  PID: $pid${NC}"
    done
else
    echo -e "${YELLOW}⚠️ Uvicorn 프로세스 없음${NC}"
fi

# npm/node 프로세스
NPM_PROCESSES=$(pgrep -f "npm.*start\|node.*react-scripts" 2>/dev/null || true)
if [[ -n "$NPM_PROCESSES" ]]; then
    echo -e "${GREEN}✅ npm/React 프로세스:${NC}"
    echo "$NPM_PROCESSES" | while read pid; do
        echo -e "${YELLOW}  PID: $pid${NC}"
    done
else
    echo -e "${YELLOW}⚠️ npm/React 프로세스 없음${NC}"
fi

echo ""

# 로그 파일 상태
echo -e "${BLUE}📋 로그 파일 상태:${NC}"

if [[ -f "$PROJECT_ROOT/backend.log" ]]; then
    BACKEND_LOG_SIZE=$(du -h "$PROJECT_ROOT/backend.log" | cut -f1)
    BACKEND_LOG_LINES=$(wc -l < "$PROJECT_ROOT/backend.log")
    echo -e "${GREEN}✅ 백엔드 로그: $BACKEND_LOG_SIZE ($BACKEND_LOG_LINES 줄)${NC}"
    echo -e "${YELLOW}  경로: $PROJECT_ROOT/backend.log${NC}"
else
    echo -e "${YELLOW}⚠️ 백엔드 로그 파일 없음${NC}"
fi

if [[ -f "$PROJECT_ROOT/frontend.log" ]]; then
    FRONTEND_LOG_SIZE=$(du -h "$PROJECT_ROOT/frontend.log" | cut -f1)
    FRONTEND_LOG_LINES=$(wc -l < "$PROJECT_ROOT/frontend.log")
    echo -e "${GREEN}✅ 프론트엔드 로그: $FRONTEND_LOG_SIZE ($FRONTEND_LOG_LINES 줄)${NC}"
    echo -e "${YELLOW}  경로: $PROJECT_ROOT/frontend.log${NC}"
else
    echo -e "${YELLOW}⚠️ 프론트엔드 로그 파일 없음${NC}"
fi

echo ""

# 데이터베이스 상태
echo -e "${BLUE}🗄️ 데이터베이스 상태:${NC}"

DB_PATH="$PROJECT_ROOT/backend/data/db.sqlite3"
if [[ -f "$DB_PATH" ]]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    echo -e "${GREEN}✅ SQLite 데이터베이스: $DB_SIZE${NC}"
    echo -e "${YELLOW}  경로: $DB_PATH${NC}"
else
    echo -e "${YELLOW}⚠️ 데이터베이스 파일 없음${NC}"
fi

# 업로드 디렉토리 상태
UPLOAD_DIR="$PROJECT_ROOT/backend/data/uploads"
if [[ -d "$UPLOAD_DIR" ]]; then
    UPLOAD_COUNT=$(find "$UPLOAD_DIR" -type f | wc -l)
    if [[ $UPLOAD_COUNT -gt 0 ]]; then
        UPLOAD_SIZE=$(du -sh "$UPLOAD_DIR" | cut -f1)
        echo -e "${GREEN}✅ 업로드 파일: $UPLOAD_COUNT 개 ($UPLOAD_SIZE)${NC}"
    else
        echo -e "${YELLOW}⚠️ 업로드 파일 없음${NC}"
    fi
    echo -e "${YELLOW}  경로: $UPLOAD_DIR${NC}"
else
    echo -e "${YELLOW}⚠️ 업로드 디렉토리 없음${NC}"
fi

echo ""

# 전체 상태 요약
echo -e "${PURPLE}📈 전체 상태 요약:${NC}"

if [[ "$BACKEND_STATUS" == "running" && "$FRONTEND_STATUS" == "running" ]]; then
    echo -e "${GREEN}✅ 시스템 상태: 정상 실행 중${NC}"
    echo -e "${BLUE}🌐 접속 URL:${NC}"
    echo -e "${GREEN}  📱 웹 애플리케이션: http://localhost:8080${NC}"
    echo -e "${GREEN}  🔧 API 서버: http://localhost:58000${NC}"
    echo -e "${GREEN}  📚 API 문서: http://localhost:58000/docs${NC}"
elif [[ "$BACKEND_STATUS" == "running" ]]; then
    echo -e "${YELLOW}⚠️ 시스템 상태: 백엔드만 실행 중${NC}"
elif [[ "$FRONTEND_STATUS" == "running" ]]; then
    echo -e "${YELLOW}⚠️ 시스템 상태: 프론트엔드만 실행 중${NC}"
else
    echo -e "${RED}❌ 시스템 상태: 중지됨${NC}"
    echo -e "${BLUE}💡 시작하려면: ./scripts/start_all.sh${NC}"
fi