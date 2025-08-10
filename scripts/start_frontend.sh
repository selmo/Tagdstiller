#!/bin/bash

# DocExtract Frontend 실행 스크립트
# 사용법: ./scripts/start_frontend.sh [dev|build]

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 기본값 설정
MODE=${1:-dev}
PORT=${PORT:-8080}

echo -e "${BLUE}🎨 DocExtract Frontend 시작${NC}"
echo -e "${YELLOW}모드: $MODE${NC}"
echo -e "${YELLOW}포트: $PORT${NC}"
echo ""

# 프로젝트 루트 디렉토리로 이동
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${BLUE}📁 프로젝트 루트: $PROJECT_ROOT${NC}"
echo -e "${BLUE}📁 프론트엔드 디렉토리: $FRONTEND_DIR${NC}"

# 프론트엔드 디렉토리 확인
if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo -e "${RED}❌ 오류: frontend 디렉토리를 찾을 수 없습니다${NC}"
    echo "예상 위치: $FRONTEND_DIR"
    exit 1
fi

cd "$FRONTEND_DIR"

# package.json 파일 확인
if [[ ! -f "package.json" ]]; then
    echo -e "${RED}❌ 오류: package.json 파일을 찾을 수 없습니다${NC}"
    echo "현재 위치: $(pwd)"
    exit 1
fi

# Node.js 버전 확인
if ! command -v node > /dev/null 2>&1; then
    echo -e "${RED}❌ 오류: Node.js가 설치되어 있지 않습니다${NC}"
    echo "Node.js를 설치해주세요: https://nodejs.org/"
    exit 1
fi

# npm 확인
if ! command -v npm > /dev/null 2>&1; then
    echo -e "${RED}❌ 오류: npm이 설치되어 있지 않습니다${NC}"
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ Node.js: $NODE_VERSION${NC}"
echo -e "${GREEN}✅ npm: $NPM_VERSION${NC}"

# 의존성 설치 확인
if [[ ! -d "node_modules" ]]; then
    echo -e "${YELLOW}📦 의존성 설치 중...${NC}"
    npm install
    echo -e "${GREEN}✅ 의존성 설치 완료${NC}"
else
    echo -e "${YELLOW}📋 의존성 확인 중...${NC}"
    # package-lock.json이 더 최신인지 확인
    if [[ "package-lock.json" -nt "node_modules" ]]; then
        echo -e "${YELLOW}📦 의존성 업데이트 중...${NC}"
        npm install
        echo -e "${GREEN}✅ 의존성 업데이트 완료${NC}"
    else
        echo -e "${GREEN}✅ 의존성이 최신 상태입니다${NC}"
    fi
fi

# 환경 변수 파일 확인
if [[ ! -f ".env" ]] && [[ ! -f ".env.local" ]]; then
    echo -e "${YELLOW}📝 환경 변수 파일 생성 중...${NC}"
    cat > .env.local << EOF
# Backend API URL
REACT_APP_API_BASE_URL=http://localhost:58000

# Development settings
REACT_APP_ENV=development
EOF
    echo -e "${GREEN}✅ .env.local 파일 생성 완료${NC}"
fi

# 포트 사용 중인지 확인
if lsof -i :$PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️ 포트 $PORT이 이미 사용 중입니다${NC}"
    echo -e "${YELLOW}다른 포트를 사용하려면: PORT=3001 ./scripts/start_frontend.sh${NC}"
    read -p "계속하시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}🎯 프론트엔드 시작 중...${NC}"

# 모드에 따른 실행
case "$MODE" in
    "dev")
        echo -e "${GREEN}🔧 개발 모드로 시작 (Hot Reload)${NC}"
        echo -e "${BLUE}📍 개발 서버: http://localhost:$PORT${NC}"
        echo ""
        echo -e "${YELLOW}서버를 중지하려면 Ctrl+C를 누르세요${NC}"
        echo ""
        PORT=$PORT npm start
        ;;
    "build")
        echo -e "${GREEN}🏗️ 프로덕션 빌드 중...${NC}"
        npm run build
        echo -e "${GREEN}✅ 빌드 완료${NC}"
        echo -e "${BLUE}📁 빌드 파일: $(pwd)/build${NC}"
        
        # 빌드 후 서브할지 물어보기
        read -p "빌드된 파일을 로컬 서버로 실행하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v serve > /dev/null 2>&1; then
                echo -e "${GREEN}🚀 정적 파일 서버 시작${NC}"
                echo -e "${BLUE}📍 서버 주소: http://localhost:$PORT${NC}"
                serve -s build -l $PORT
            else
                echo -e "${YELLOW}⚠️ 'serve' 패키지가 설치되어 있지 않습니다${NC}"
                echo -e "${YELLOW}설치: npm install -g serve${NC}"
                echo -e "${YELLOW}수동 실행: npx serve -s build -l $PORT${NC}"
            fi
        fi
        ;;
    "test")
        echo -e "${GREEN}🧪 테스트 실행${NC}"
        npm test
        ;;
    *)
        echo -e "${RED}❌ 알 수 없는 모드: $MODE${NC}"
        echo "사용 가능한 모드: dev, build, test"
        exit 1
        ;;
esac