#!/usr/bin/env python3
"""
엔티티 간 직접 관계 추출 테스트

사용법:
cd /Users/selmo/Workspaces/DocExtract
PYTHONPATH=backend python test/test_entity_relationships.py
"""

import sys
import os
import json
from pathlib import Path

# 백엔드 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.hierarchical_kg_builder import HierarchicalKGBuilder

def test_entity_relationships():
    """엔티티 간 관계 추출 테스트"""
    
    # 테스트 문서 경로
    test_doc_path = "test/hierarchical_kg_test_document.md"
    
    print("🧪 엔티티 간 관계 추출 테스트 시작")
    print(f"📄 테스트 문서: {test_doc_path}")
    
    # 문서 읽기
    try:
        with open(test_doc_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
    except FileNotFoundError:
        print(f"❌ 테스트 문서를 찾을 수 없습니다: {test_doc_path}")
        return
    
    # 모의 키워드 데이터 생성
    mock_keywords = {
        "llm": [
            {"keyword": "FastAPI", "score": 0.95, "category": "technology"},
            {"keyword": "PostgreSQL", "score": 0.92, "category": "database"},
            {"keyword": "SQLAlchemy", "score": 0.88, "category": "framework"},
            {"keyword": "Redis", "score": 0.85, "category": "database"},
            {"keyword": "Docker", "score": 0.82, "category": "tool"},
            {"keyword": "RESTful", "score": 0.90, "category": "concept"},
            {"keyword": "JWT", "score": 0.87, "category": "technology"}
        ]
    }
    
    # 기본 메타데이터
    metadata = {
        "name": "hierarchical_kg_test_document.md",
        "size": len(document_text),
        "extension": ".md"
    }
    
    # 계층적 KG 빌더 생성 (Memgraph 비활성화)
    kg_builder = HierarchicalKGBuilder(auto_save_to_memgraph=False)
    
    print("🏗️ 계층적 KG 구축 중...")
    
    # KG 구축
    result = kg_builder.build_hierarchical_knowledge_graph(
        file_path=test_doc_path,
        document_text=document_text,
        keywords=mock_keywords,
        metadata=metadata,
        force_rebuild=True
    )
    
    print(f"✅ KG 구축 완료!")
    print(f"📊 총 엔티티: {len(result['entities'])}개")
    print(f"🔗 총 관계: {len(result['relationships'])}개")
    
    # 관계 유형별 분석
    relationship_types = {}
    entity_to_entity_relationships = []
    
    for rel in result["relationships"]:
        rel_name = rel.get("properties", {}).get("relationship_name", "UNKNOWN")
        relationship_types[rel_name] = relationship_types.get(rel_name, 0) + 1
        
        # 엔티티 간 직접 관계 필터링
        if rel.get("properties", {}).get("entity_to_entity"):
            entity_to_entity_relationships.append(rel)
    
    print(f"\n📈 관계 유형 분포:")
    for rel_type, count in sorted(relationship_types.items()):
        print(f"  - {rel_type}: {count}개")
    
    print(f"\n🎯 엔티티 간 직접 관계: {len(entity_to_entity_relationships)}개")
    
    if entity_to_entity_relationships:
        print("\n🔍 엔티티 간 관계 상세:")
        
        # 엔티티 ID를 텍스트로 매핑하는 맵 생성
        entity_text_map = {}
        for entity in result["entities"]:
            if entity.get("properties", {}).get("hierarchical_entity"):
                entity_text_map[entity["id"]] = entity.get("properties", {}).get("text", entity["id"])
        
        for i, rel in enumerate(entity_to_entity_relationships[:10], 1):  # 상위 10개만 표시
            source_text = entity_text_map.get(rel["source"], rel["source"])
            target_text = entity_text_map.get(rel["target"], rel["target"])
            rel_name = rel.get("properties", {}).get("relationship_name", "UNKNOWN")
            confidence = rel.get("properties", {}).get("confidence_score", 0)
            extraction_method = rel.get("properties", {}).get("extraction_method", "unknown")
            
            print(f"  {i:2d}. {source_text} --[{rel_name}]--> {target_text}")
            print(f"      신뢰도: {confidence:.2f}, 추출방법: {extraction_method}")
            
            if rel.get("properties", {}).get("context_snippet"):
                context = rel["properties"]["context_snippet"]
                print(f"      컨텍스트: \"{context}\"")
            print()
    else:
        print("⚠️  엔티티 간 직접 관계가 발견되지 않았습니다.")
        
        # 디버깅을 위한 추가 정보
        print(f"\n🔍 디버깅 정보:")
        
        keyword_entities = [e for e in result["entities"] if e.get("properties", {}).get("hierarchical_entity")]
        print(f"  - 키워드 엔티티 수: {len(keyword_entities)}개")
        
        if keyword_entities:
            print(f"  - 키워드 엔티티 샘플:")
            for entity in keyword_entities[:5]:
                entity_text = entity.get("properties", {}).get("text", "")
                entity_type = entity.get("type", "")
                source_structure = entity.get("properties", {}).get("source_structure", "")
                print(f"    * {entity_text} ({entity_type}) from {source_structure}")
    
    # 결과를 파일로 저장
    output_file = "test/entity_relationships_test_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 전체 결과가 {output_file}에 저장되었습니다.")
    print("🎉 테스트 완료!")

if __name__ == "__main__":
    test_entity_relationships()