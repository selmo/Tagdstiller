#!/bin/bash

echo "==================================="
echo "🧪 모든 파서 메타데이터 추출 테스트"
echo "==================================="

# 테스트 파일
TEST_FILE="test_document.pdf"
echo "테스트 파일: $TEST_FILE"
echo ""

# 1. 기본 동작 테스트 (use_docling 파라미터 없음 = 모든 파서 시도)
echo "1️⃣ 기본 동작 (모든 파서 시도)..."
curl -s -G "http://localhost:58000/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'시도한 파서: {data.get(\"parsers_attempted\", [])}')
print(f'최상의 결과: {data.get(\"best_result\", \"None\")}')
results = data.get('parsers_results', {})
for parser, result in results.items():
    success = result.get('success', False)
    score = result.get('score', 0)
    status = '✅' if success else '❌'
    print(f'  {status} {parser}: 점수={score}')
"

echo ""

# 2. 기본 파서만 사용
echo "2️⃣ 기본 파서만 사용 (use_docling=false)..."
curl -s -G "http://localhost:58000/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    --data-urlencode "use_docling=false" \
    | python -c "
import sys, json
data = json.load(sys.stdin)
parser = data.get('parser_used', data.get('processing:parserName', 'unknown'))
print(f'사용된 파서: {parser}')
"

echo ""

# 3. Docling 파서만 사용
echo "3️⃣ Docling 파서만 사용 (use_docling=true)..."
curl -s -G "http://localhost:58000/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    --data-urlencode "use_docling=true" \
    | python -c "
import sys, json
data = json.load(sys.stdin)
parser = data.get('parser_used', data.get('processing:parserName', 'unknown'))
print(f'사용된 파서: {parser}')
has_structure = 'docling_structure' in data
print(f'Docling 구조 정보: {\"있음\" if has_structure else \"없음\"}')
"

echo ""

# 4. 명시적으로 모든 파서 시도
echo "4️⃣ 명시적 모든 파서 (use_all_parsers=true)..."
curl -s -G "http://localhost:58000/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    --data-urlencode "use_all_parsers=true" \
    | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'시도한 파서: {data.get(\"parsers_attempted\", [])}')
"

echo ""

# 5. 저장된 파일 확인
echo "5️⃣ 저장된 파일 확인..."
ls -la test_document.pdf.*.json 2>/dev/null | tail -5

echo ""
echo "==================================="
echo "✅ 테스트 완료"
echo "===================================" 