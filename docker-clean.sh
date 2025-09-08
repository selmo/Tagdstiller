#!/bin/bash

# DocExtract Docker 정리 스크립트

set -e

echo "🧹 DocExtract Docker 환경 정리 중..."

# 확인 메시지
read -p "⚠️  모든 컨테이너, 이미지, 볼륨을 삭제하시겠습니까? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 정리 작업이 취소되었습니다."
    exit 1
fi

# 서비스 중지 및 삭제
echo "📦 Docker 서비스 중지 및 컨테이너 삭제 중..."
docker-compose down -v --remove-orphans

# 이미지 삭제
echo "🖼️  DocExtract 관련 이미지 삭제 중..."
docker images | grep -E "(docextract|memgraph)" | awk '{print $3}' | xargs -r docker rmi -f

# 볼륨 삭제
echo "💾 DocExtract 관련 볼륨 삭제 중..."
docker volume ls | grep -E "(docextract|memgraph)" | awk '{print $2}' | xargs -r docker volume rm

# 네트워크 삭제
echo "🌐 DocExtract 네트워크 삭제 중..."
docker network ls | grep docextract | awk '{print $1}' | xargs -r docker network rm

# 사용하지 않는 리소스 정리
echo "🗑️  사용하지 않는 Docker 리소스 정리 중..."
docker system prune -f

echo ""
echo "✅ DocExtract Docker 환경이 완전히 정리되었습니다!"
echo "🔄 다시 시작하려면: ./docker-start.sh"