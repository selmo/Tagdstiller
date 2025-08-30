#!/bin/bash

# Local Analysis Metadata API 테스트 스크립트

echo "=== Local Analysis Metadata API 테스트 ==="
echo ""
PORT=${PORT:-8001}
echo "사용 포트: $PORT"
echo ""

# 1. 현재 디렉토리 확인
echo "1. 현재 디렉토리 확인:"
curl -s "http://localhost:$PORT/local-analysis/config/current-directory" | python -m json.tool | head -10
echo "..."
echo ""

# 2. 테스트 파일 생성
echo "2. 테스트 파일 생성:"
echo "This is a test document for metadata extraction.
It contains multiple lines and paragraphs.

This is the second paragraph with some sample text.
We can extract metadata from this file without keyword extraction." > /tmp/test_metadata.txt
echo "테스트 파일 생성됨: /tmp/test_metadata.txt"
echo ""

# 3. 메타데이터 추출 (GET 방식)
echo "3. 메타데이터 추출 (GET 방식):"
curl -s "http://localhost:$PORT/local-analysis/metadata?file_path=/tmp/test_metadata.txt" | python -m json.tool
echo ""

# 4. 메타데이터 추출 (POST 방식) 
echo "4. 메타데이터 추출 (POST 방식):"
curl -s -X POST "http://localhost:$PORT/local-analysis/metadata" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "/tmp/test_metadata.txt"}' | python -m json.tool
echo ""

echo "=== 테스트 완료 ==="