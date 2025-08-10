#!/bin/bash

# DocExtract Backend 실행 스크립트
# 사용법: ./scripts/start_backend.sh [dev|prod]

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본값 설정
MODE=${1:-dev}
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-58000}
CONDA_ENV=${CONDA_ENV:-"DocExtract"}

echo -e "${BLUE}🚀 DocExtract Backend 시작${NC}"
echo -e "${YELLOW}모드: $MODE${NC}"
echo -e "${YELLOW}호스트: $HOST${NC}"
echo -e "${YELLOW}포트: $PORT${NC}"
echo -e "${YELLOW}Conda 환경: $CONDA_ENV${NC}"
echo ""

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo -e "${BLUE}📁 프로젝트 루트: $PROJECT_ROOT${NC}"
echo -e "${BLUE}📁 백엔드 디렉토리: $BACKEND_DIR${NC}"

# 백엔드 디렉토리 확인
if [[ ! -d "$BACKEND_DIR" ]]; then
    echo -e "${RED}❌ 오류: backend 디렉토리를 찾을 수 없습니다${NC}"
    echo "예상 위치: $BACKEND_DIR"
    exit 1
fi

cd "$BACKEND_DIR"

# main.py 파일 확인
if [[ ! -f "main.py" ]]; then
    echo -e "${RED}❌ 오류: main.py 파일을 찾을 수 없습니다${NC}"
    echo "현재 위치: $(pwd)"
    exit 1
fi

# Conda 확인
if ! command -v conda > /dev/null 2>&1; then
    echo -e "${RED}❌ 오류: conda가 설치되어 있지 않습니다${NC}"
    echo "Anaconda 또는 Miniconda를 설치해주세요: https://conda.io/projects/conda/en/latest/user-guide/install/index.html"
    exit 1
fi

# Conda 환경 확인 및 생성
if ! conda info --envs | grep -q "^${CONDA_ENV}\s"; then
    echo -e "${YELLOW}📦 Conda 환경 생성 중: $CONDA_ENV${NC}"
    conda create -n $CONDA_ENV python=3.11 -y
    echo -e "${GREEN}✅ Conda 환경 생성 완료${NC}"
else
    echo -e "${GREEN}✅ Conda 환경 확인: $CONDA_ENV${NC}"
fi

# Conda 환경 활성화
echo -e "${YELLOW}🔄 Conda 환경 활성화 중: $CONDA_ENV${NC}"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate $CONDA_ENV

# 의존성 설치 확인
echo -e "${YELLOW}📋 의존성 확인 중...${NC}"
if [[ ! -f "requirements.txt" ]]; then
    echo -e "${RED}❌ requirements.txt 파일이 없습니다${NC}"
    exit 1
fi

# pip 업그레이드
echo -e "${YELLOW}🔄 pip 업그레이드 중...${NC}"
pip install --upgrade pip > /dev/null 2>&1

# 의존성 설치
echo -e "${YELLOW}📦 의존성 설치 중...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}✅ 의존성 설치 완료${NC}"

# 데이터 디렉토리 생성
if [[ ! -d "data" ]]; then
    echo -e "${YELLOW}📁 데이터 디렉토리 생성 중...${NC}"
    mkdir -p data/uploads
    echo -e "${GREEN}✅ 데이터 디렉토리 생성 완료${NC}"
fi

# 데이터베이스 초기화 확인
if [[ ! -f "data/db.sqlite3" ]]; then
    echo -e "${YELLOW}🗄️ 데이터베이스 초기화 중...${NC}"
    python -c "from main import app; print('Database initialized')" > /dev/null 2>&1
    echo -e "${GREEN}✅ 데이터베이스 초기화 완료${NC}"
fi

# 포트 사용 중인지 확인
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 포트 $PORT이 이미 사용 중입니다${NC}"
    echo -e "${YELLOW}다른 포트를 사용하려면: PORT=8001 ./scripts/start_backend.sh${NC}"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎯 서버 시작 중...${NC}"
echo -e "${BLUE}📍 서버 주소: http://localhost:$PORT${NC}"
echo -e "${BLUE}📚 API 문서: http://localhost:$PORT/docs${NC}"
echo -e "${BLUE}🛠️ 대체 문서: http://localhost:$PORT/redoc${NC}"
echo ""
echo -e "${YELLOW}서버를 중지하려면 Ctrl+C를 누르세요${NC}"
echo ""

# 서버 실행
if [[ "$MODE" == "prod" ]]; then
    echo -e "${GREEN}🏭 프로덕션 모드로 시작${NC}"
    uvicorn main:app --host $HOST --port $PORT
else
    echo -e "${GREEN}🔧 개발 모드로 시작 (자동 리로드)${NC}"
    uvicorn main:app --reload --host $HOST --port $PORT
fi