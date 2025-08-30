#!/bin/bash

# Local Analysis API 테스트 스크립트

echo "=== Local Analysis API 테스트 ==="
echo ""

# 1. 현재 디렉토리 확인 (GET 요청으로!)
echo "1. 현재 디렉토리 확인 (GET):"
curl "http://localhost:8001/local-analysis/config/current-directory"
echo -e "\n"

# 2. 디렉토리 변경 (directory 키 사용!)
echo "2. 디렉토리 변경 (directory 키 사용):"
curl -X POST "http://localhost:8001/local-analysis/config/change-directory" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/Users/selmo/Documents"}'
echo -e "\n"

# 3. 파일 루트 디렉토리 확인
echo "3. 파일 루트 디렉토리 확인:"
curl "http://localhost:8001/local-analysis/config/root"
echo -e "\n"

# 4. 사용 가능한 추출기 목록
echo "4. 사용 가능한 추출기 목록:"
curl "http://localhost:8001/local-analysis/config/extractors"
echo -e "\n"

# 5. 파일 상태 확인 (예시)
echo "5. 파일 상태 확인:"
curl "http://localhost:8001/local-analysis/status?file_path=test_document.txt"
echo -e "\n"

echo "=== 테스트 완료 ==="