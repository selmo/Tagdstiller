#!/bin/bash

echo "==================================="
echo "🧪 Metadata 엔드포인트 Docling 테스트"
echo "==================================="

# 백엔드 서버 포트 설정
PORT=${1:-58000}
echo "포트: $PORT"

# 테스트 파일 설정
TEST_FILE="2. 통화신용정책 운영.pdf"
echo "테스트 파일: $TEST_FILE"
echo ""

# 1. 기본 파서로 메타데이터 추출
echo "1️⃣ 기본 파서로 메타데이터 추출..."
curl -s -G "http://localhost:$PORT/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    | python -m json.tool > /tmp/metadata_default.json

if [ $? -eq 0 ]; then
    echo "   ✅ 성공"
    echo "   파서: $(cat /tmp/metadata_default.json | python -c "import sys, json; print(json.load(sys.stdin).get('parser_used', 'unknown'))" 2>/dev/null)"
else
    echo "   ❌ 실패"
fi

echo ""

# 2. Docling 파서로 메타데이터 추출
echo "2️⃣ Docling 파서로 메타데이터 추출..."
curl -s -G "http://localhost:$PORT/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    --data-urlencode "use_docling=true" \
    | python -m json.tool > /tmp/metadata_docling.json

if [ $? -eq 0 ]; then
    echo "   ✅ 성공"
    echo "   파서: $(cat /tmp/metadata_docling.json | python -c "import sys, json; print(json.load(sys.stdin).get('parser_used', 'unknown'))" 2>/dev/null)"
    
    # Docling 구조 정보 확인
    HAS_STRUCTURE=$(cat /tmp/metadata_docling.json | python -c "import sys, json; print('docling_structure' in json.load(sys.stdin))" 2>/dev/null)
    if [ "$HAS_STRUCTURE" = "True" ]; then
        echo "   📊 Docling 구조 정보: 있음"
        
        # 테이블 개수 확인
        TABLE_COUNT=$(cat /tmp/metadata_docling.json | python -c "
import sys, json
data = json.load(sys.stdin)
structure = data.get('docling_structure', {})
tables = structure.get('tables', [])
print(len(tables))
" 2>/dev/null)
        echo "   📋 테이블 수: $TABLE_COUNT"
        
        # 섹션 개수 확인
        SECTION_COUNT=$(cat /tmp/metadata_docling.json | python -c "
import sys, json
data = json.load(sys.stdin)
structure = data.get('docling_structure', {})
sections = structure.get('sections', [])
print(len(sections))
" 2>/dev/null)
        echo "   📑 섹션 수: $SECTION_COUNT"
    else
        echo "   📊 Docling 구조 정보: 없음"
    fi
    
    # 저장된 파일 확인
    METADATA_FILE=$(cat /tmp/metadata_docling.json | python -c "import sys, json; print(json.load(sys.stdin).get('metadata_file', ''))" 2>/dev/null)
    MARKDOWN_FILE=$(cat /tmp/metadata_docling.json | python -c "import sys, json; print(json.load(sys.stdin).get('markdown_file', ''))" 2>/dev/null)
    
    if [ -n "$METADATA_FILE" ]; then
        echo "   💾 메타데이터 파일: $(basename "$METADATA_FILE")"
    fi
    if [ -n "$MARKDOWN_FILE" ]; then
        echo "   📝 Markdown 파일: $(basename "$MARKDOWN_FILE")"
    fi
else
    echo "   ❌ 실패"
fi

echo ""
echo "==================================="
echo "📊 결과 파일"
echo "==================================="
echo "기본 파서: /tmp/metadata_default.json"
echo "Docling 파서: /tmp/metadata_docling.json"
echo ""

# 파일 크기 비교
if [ -f /tmp/metadata_default.json ] && [ -f /tmp/metadata_docling.json ]; then
    DEFAULT_SIZE=$(stat -f%z /tmp/metadata_default.json 2>/dev/null || stat -c%s /tmp/metadata_default.json 2>/dev/null)
    DOCLING_SIZE=$(stat -f%z /tmp/metadata_docling.json 2>/dev/null || stat -c%s /tmp/metadata_docling.json 2>/dev/null)
    echo "파일 크기:"
    echo "  기본: $DEFAULT_SIZE bytes"
    echo "  Docling: $DOCLING_SIZE bytes"
fi

echo "==================================="