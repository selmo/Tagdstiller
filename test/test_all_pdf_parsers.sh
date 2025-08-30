#!/bin/bash

echo "==================================="
echo "🧪 모든 PDF 파서 개별 테스트"
echo "==================================="

# 테스트 파일
TEST_FILE="test_document.pdf"
echo "테스트 파일: $TEST_FILE"
echo ""

# 1. 모든 파서 자동 시도 (기본 동작)
echo "1️⃣ 모든 PDF 파서 자동 시도..."
curl -s -G "http://localhost:58000/local-analysis/metadata" \
    --data-urlencode "file_path=$TEST_FILE" \
    --max-time 60 \
    | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'시도한 파서: {data.get(\"parsers_attempted\", [])}')
print(f'최상의 결과: {data.get(\"best_result\", \"None\")}')
print('')
print('파서별 결과:')
results = data.get('parsers_results', {})
for parser, result in results.items():
    success = result.get('success', False)
    score = result.get('score', 0)
    status = '✅' if success else '❌'
    parser_used = result.get('metadata', {}).get('parser_used', parser)
    print(f'  {status} {parser:15} 점수={score:3} 파서={parser_used}')
" 2>/dev/null || echo "타임아웃 또는 오류"

echo ""
echo ""

# 2. 저장된 파일 확인
echo "2️⃣ 저장된 파일 확인..."
echo "개별 파서 결과 파일:"
ls -la test_document.pdf.*.json 2>/dev/null | grep -v "all_parsers" | tail -10

echo ""

# 3. 파일 크기 비교
echo "3️⃣ 파일 크기 비교..."
for file in test_document.pdf.*.json; do
    if [ -f "$file" ] && [[ ! "$file" == *"all_parsers"* ]]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        basename=$(basename "$file")
        printf "  %-40s %8d bytes\n" "$basename" "$size"
    fi
done

echo ""
echo "==================================="
echo "✅ 테스트 완료"
echo "===================================" 