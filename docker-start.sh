#!/bin/bash

# DocExtract Docker 시작 스크립트

set -e

echo "🐳 DocExtract Docker 환경 시작 중..."

# 환경 변수 로드
if [ -f .env ]; then
    echo "📄 환경 변수 파일 로드 중..."
    export $(cat .env | grep -v ^# | xargs)
fi

# 필요한 디렉토리 생성
echo "📁 필요한 디렉토리 생성 중..."
mkdir -p data uploads logs

# Docker Compose로 서비스 시작
echo "🚀 Docker 서비스 시작 중..."
docker-compose up -d

# 서비스 상태 확인
echo "⏳ 서비스 시작 대기 중..."
sleep 10

echo "🔍 서비스 상태 확인 중..."
docker-compose ps

echo ""
echo "✅ DocExtract Docker 환경이 시작되었습니다!"
echo ""
echo "🌐 서비스 접속 정보:"
echo "  - DocExtract API: http://localhost:58000"
echo "  - API 문서: http://localhost:58000/docs"
echo "  - Memgraph Studio: http://localhost:3000"
echo "  - Memgraph Bolt: bolt://localhost:7687"
echo ""
echo "📋 유용한 명령어:"
echo "  - 로그 보기: docker-compose logs -f"
echo "  - 서비스 중지: docker-compose down"
echo "  - 서비스 재시작: docker-compose restart"
echo "  - 컨테이너 상태: docker-compose ps"
echo ""

# 서비스 헬스체크
echo "🏥 서비스 헬스체크 중..."
sleep 5

# DocExtract API 확인
if curl -s http://localhost:58000/docs > /dev/null; then
    echo "✅ DocExtract API 정상 작동 중"
else
    echo "❌ DocExtract API 접속 실패"
fi

# Memgraph Studio 확인
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Memgraph Studio 정상 작동 중"
else
    echo "❌ Memgraph Studio 접속 실패"
fi

echo ""
echo "🎉 모든 서비스가 준비되었습니다!"