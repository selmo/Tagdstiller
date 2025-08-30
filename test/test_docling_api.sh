#!/bin/bash

echo "==================================="
echo "🧪 Docling 파서 API 테스트"
echo "==================================="

# 백엔드 서버가 실행 중인지 확인
echo -n "백엔드 서버 상태 확인... "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 실행 중"
else
    echo "❌ 서버가 실행되지 않음"
    echo "서버를 먼저 시작하세요: ./scripts/start_backend.sh"
    exit 1
fi

# 테스트 파일 경로
TEST_FILE="/Users/selmo/Workspaces/RAG-Evaluation-Dataset-KO/finance/★2019 제1회 증시콘서트 자료집_최종★.pdf"

echo ""
echo "📄 테스트 파일: $(basename "$TEST_FILE")"
echo ""

# 1. 기본 파서로 분석 (빠른 처리)
echo "1️⃣ 기본 파서로 분석 중..."
START_TIME=$(date +%s)
curl -s "http://localhost:8000/local-analysis/analyze?file_path=${TEST_FILE}&extractors=metadata&force_reanalyze=true" \
    | python -m json.tool > /tmp/default_parser_result.json
END_TIME=$(date +%s)
DEFAULT_TIME=$((END_TIME - START_TIME))

if [ -f /tmp/default_parser_result.json ]; then
    echo "   ✅ 완료 (소요시간: ${DEFAULT_TIME}초)"
    echo "   텍스트 길이: $(cat /tmp/default_parser_result.json | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('content_info', {}).get('length', 'N/A'))" 2>/dev/null)"
else
    echo "   ❌ 실패"
fi

echo ""

# 2. Docling 파서로 분석 (구조 추출)
echo "2️⃣ Docling 파서로 분석 중 (시간이 걸릴 수 있습니다)..."
START_TIME=$(date +%s)
timeout 30 curl -s "http://localhost:8000/local-analysis/analyze?file_path=${TEST_FILE}&extractors=metadata&force_reanalyze=true&use_docling=true" \
    | python -m json.tool > /tmp/docling_parser_result.json 2>/dev/null
END_TIME=$(date +%s)
DOCLING_TIME=$((END_TIME - START_TIME))

if [ -f /tmp/docling_parser_result.json ] && [ -s /tmp/docling_parser_result.json ]; then
    echo "   ✅ 완료 (소요시간: ${DOCLING_TIME}초)"
    echo "   텍스트 길이: $(cat /tmp/docling_parser_result.json | python -c "import sys, json; data=json.load(sys.stdin); print(data.get('content_info', {}).get('length', 'N/A'))" 2>/dev/null)"
else
    echo "   ⚠️  타임아웃 또는 처리 실패 (30초 제한)"
fi

echo ""
echo "==================================="
echo "📊 테스트 결과 요약"
echo "==================================="
echo "기본 파서: ${DEFAULT_TIME}초"
echo "Docling 파서: ${DOCLING_TIME}초 (또는 타임아웃)"
echo ""
echo "결과 파일:"
echo "  - 기본: /tmp/default_parser_result.json"
echo "  - Docling: /tmp/docling_parser_result.json"
echo "===================================" 