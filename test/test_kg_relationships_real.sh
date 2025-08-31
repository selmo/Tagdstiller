#!/bin/bash

# 실제 시스템에서 엔티티 간 관계 테스트

echo "🧪 실제 시스템에서 엔티티 간 관계 테스트 시작"
echo "📄 테스트 문서: test/hierarchical_kg_test_document.md"

# 백엔드 실행 확인
echo "⚡ 백엔드 서버 상태 확인..."
if ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo "❌ 백엔드 서버가 실행되지 않았습니다. scripts/start_backend.sh 를 실행해주세요."
    exit 1
fi

echo "✅ 백엔드 서버 연결됨"

# 계층적 KG 생성 요청
echo "🏗️ 계층적 KG 생성 중..."
response=$(curl -s -X POST "http://localhost:8001/local-analysis/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "test/hierarchical_kg_test_document.md",
    "force_rebuild": true
  }')

# 응답 확인
if [[ $? -eq 0 ]] && [[ -n "$response" ]]; then
    echo "✅ KG 생성 완료"
    
    # 응답을 JSON 파일로 저장
    echo "$response" > test/kg_real_system_result.json
    echo "💾 결과가 test/kg_real_system_result.json에 저장되었습니다"
    
    # 관계 분석
    entity_count=$(echo "$response" | jq '.entities | length')
    relationship_count=$(echo "$response" | jq '.relationships | length')
    
    echo "📊 KG 통계:"
    echo "  - 총 엔티티: ${entity_count}개"
    echo "  - 총 관계: ${relationship_count}개"
    
    # 엔티티 간 직접 관계 확인
    entity_relationships=$(echo "$response" | jq '.relationships[] | select(.properties.entity_to_entity == true)')
    entity_rel_count=$(echo "$entity_relationships" | jq -s 'length')
    
    echo "  - 엔티티 간 직접 관계: ${entity_rel_count}개"
    
    if [[ $entity_rel_count -gt 0 ]]; then
        echo "🎉 성공! 엔티티 간 관계가 추출되었습니다"
        
        # 관계 타입 분포 분석
        echo "🔗 관계 타입 분포:"
        echo "$response" | jq -r '.relationships[] | .properties.relationship_name' | sort | uniq -c | sort -nr
        
    else
        echo "⚠️  엔티티 간 관계가 추출되지 않았습니다"
    fi
    
else
    echo "❌ KG 생성 실패"
    echo "응답: $response"
fi

echo "🏁 테스트 완료"