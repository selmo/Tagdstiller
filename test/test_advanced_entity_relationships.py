#!/usr/bin/env python3
"""
고급 엔티티 간 관계 추출 테스트 (실제 구조 분석 포함)

사용법:
cd /Users/selmo/Workspaces/DocExtract
PYTHONPATH=backend python test/test_advanced_entity_relationships.py
"""

import sys
import os
import json
from pathlib import Path

# 백엔드 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.hierarchical_kg_builder import HierarchicalKGBuilder

def create_mock_structure_analysis():
    """모의 구조 분석 결과 생성"""
    return {
        "structure_elements": {
            "sections": [
                {
                    "title": "기술 스택",
                    "level": 2,
                    "content": "FastAPI: 고성능 Python 웹 프레임워크\nSQLAlchemy: 데이터베이스 ORM\nPydantic: 데이터 검증 라이브러리"
                },
                {
                    "title": "데이터베이스", 
                    "level": 2,
                    "content": "PostgreSQL: 메인 DB, ACID 준수, 확장성\nRedis: 캐싱, 고속 인메모리 저장\nElasticsearch: 검색, 전문 검색 엔진"
                }
            ],
            "tables": [
                {
                    "content": "| 데이터베이스 | 용도 | 장점 |\n|-------------|------|------|\n| PostgreSQL  | 메인 DB | ACID 준수, 확장성 |\n| Redis       | 캐싱 | 고속 인메모리 저장 |\n| Elasticsearch | 검색 | 전문 검색 엔진 |",
                    "page": 1,
                    "rows": [
                        ["데이터베이스", "용도", "장점"],
                        ["PostgreSQL", "메인 DB", "ACID 준수, 확장성"],
                        ["Redis", "캐싱", "고속 인메모리 저장"],
                        ["Elasticsearch", "검색", "전문 검색 엔진"]
                    ]
                }
            ]
        },
        "summary": {
            "best_parser": "base_parser"
        }
    }

def create_mock_parsing_results():
    """모의 파싱 결과 생성"""
    return {
        "parsing_results": {
            "base_parser": {
                "structured_info": {
                    "document_structure": {
                        "sections": [
                            {
                                "title": "기술 스택",
                                "level": 2,
                                "line": 7,
                                "content": "FastAPI: 고성능 Python 웹 프레임워크\nSQLAlchemy: 데이터베이스 ORM\nPydantic: 데이터 검증 라이브러리"
                            },
                            {
                                "title": "데이터베이스",
                                "level": 2, 
                                "line": 15,
                                "content": "PostgreSQL: 메인 DB, ACID 준수, 확장성\nRedis: 캐싱, 고속 인메모리 저장\nElasticsearch: 검색, 전문 검색 엔진"
                            }
                        ],
                        "tables": [
                            {
                                "content": "| 데이터베이스 | 용도 | 장점 |\n|-------------|------|------|\n| PostgreSQL  | 메인 DB | ACID 준수, 확장성 |\n| Redis       | 캐싱 | 고속 인메모리 저장 |\n| Elasticsearch | 검색 | 전문 검색 엔진 |",
                                "page": 1,
                                "rows": [
                                    ["데이터베이스", "용도", "장점"],
                                    ["PostgreSQL", "메인 DB", "ACID 준수, 확장성"],
                                    ["Redis", "캐싱", "고속 인메모리 저장"], 
                                    ["Elasticsearch", "검색", "전문 검색 엔진"]
                                ],
                                "columns": ["데이터베이스", "용도", "장점"]
                            }
                        ]
                    }
                }
            }
        },
        "summary": {
            "best_parser": "base_parser"
        }
    }

def test_advanced_entity_relationships():
    """고급 엔티티 간 관계 추출 테스트"""
    
    # 테스트 문서 경로
    test_doc_path = "test/hierarchical_kg_test_document.md"
    
    print("🧪 고급 엔티티 간 관계 추출 테스트 시작")
    print(f"📄 테스트 문서: {test_doc_path}")
    
    # 문서 읽기
    try:
        with open(test_doc_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
    except FileNotFoundError:
        print(f"❌ 테스트 문서를 찾을 수 없습니다: {test_doc_path}")
        return
    
    # 구조별로 분산된 키워드 데이터 생성
    mock_keywords = {
        "llm": [
            # 기술 스택 섹션에서 발견될 키워드들
            {"keyword": "FastAPI", "score": 0.95, "category": "technology", "start_position": 300, "end_position": 307},
            {"keyword": "SQLAlchemy", "score": 0.88, "category": "framework", "start_position": 350, "end_position": 360},
            {"keyword": "Pydantic", "score": 0.85, "category": "framework", "start_position": 380, "end_position": 388},
            
            # 데이터베이스 섹션에서 발견될 키워드들  
            {"keyword": "PostgreSQL", "score": 0.92, "category": "database", "start_position": 500, "end_position": 510},
            {"keyword": "Redis", "score": 0.87, "category": "database", "start_position": 550, "end_position": 555},
            {"keyword": "Elasticsearch", "score": 0.82, "category": "database", "start_position": 600, "end_position": 613},
            
            # 공통 개념들
            {"keyword": "RESTful", "score": 0.90, "category": "concept"},
            {"keyword": "API", "score": 0.93, "category": "concept"},
            {"keyword": "ORM", "score": 0.89, "category": "concept"}
        ]
    }
    
    # 기본 메타데이터
    metadata = {
        "name": "hierarchical_kg_test_document.md",
        "size": len(document_text),
        "extension": ".md"
    }
    
    # 모의 구조 분석과 파싱 결과 생성
    structure_analysis = create_mock_structure_analysis()
    parsing_results = create_mock_parsing_results()
    
    # 계층적 KG 빌더 생성 (Memgraph 비활성화)
    kg_builder = HierarchicalKGBuilder(auto_save_to_memgraph=False)
    
    print("🏗️ 계층적 KG 구축 중... (구조 분석 포함)")
    
    # KG 구축
    result = kg_builder.build_hierarchical_knowledge_graph(
        file_path=test_doc_path,
        document_text=document_text,
        keywords=mock_keywords,
        metadata=metadata,
        structure_analysis=structure_analysis,
        parsing_results=parsing_results,
        force_rebuild=True
    )
    
    print(f"✅ KG 구축 완료!")
    print(f"📊 총 엔티티: {len(result['entities'])}개")
    print(f"🔗 총 관계: {len(result['relationships'])}개")
    
    # 엔티티 분석
    document_entities = [e for e in result["entities"] if e["type"] == "Document"]
    structure_entities = [e for e in result["entities"] if e.get("properties", {}).get("structural_element")]
    keyword_entities = [e for e in result["entities"] if e.get("properties", {}).get("hierarchical_entity")]
    
    print(f"\n📈 엔티티 분포:")
    print(f"  - 문서 엔티티: {len(document_entities)}개")
    print(f"  - 구조 엔티티: {len(structure_entities)}개") 
    print(f"  - 키워드 엔티티: {len(keyword_entities)}개")
    
    # 관계 유형별 분석
    relationship_types = {}
    structure_relationships = []
    entity_relationships = []
    
    for rel in result["relationships"]:
        rel_name = rel.get("properties", {}).get("relationship_name", "UNKNOWN")
        relationship_types[rel_name] = relationship_types.get(rel_name, 0) + 1
        
        # 구조 관계 vs 엔티티 관계 분류
        if rel["type"] == "CONTAINS_STRUCTURE":
            structure_relationships.append(rel)
        elif rel.get("properties", {}).get("entity_to_entity"):
            entity_relationships.append(rel)
    
    print(f"\n🔗 관계 유형 분포:")
    for rel_type, count in sorted(relationship_types.items()):
        print(f"  - {rel_type}: {count}개")
    
    print(f"\n🎯 관계 카테고리:")
    print(f"  - 구조 관계: {len(structure_relationships)}개")
    print(f"  - 엔티티 간 직접 관계: {len(entity_relationships)}개")
    
    if entity_relationships:
        print(f"\n🔍 엔티티 간 관계 상세 (상위 15개):")
        
        # 엔티티 ID를 텍스트로 매핑
        entity_text_map = {}
        entity_type_map = {}
        for entity in result["entities"]:
            if entity.get("properties", {}).get("hierarchical_entity"):
                entity_text_map[entity["id"]] = entity.get("properties", {}).get("text", entity["id"])
                entity_type_map[entity["id"]] = entity.get("type", "Unknown")
        
        # 관계를 신뢰도순으로 정렬
        sorted_relationships = sorted(entity_relationships, 
                                    key=lambda x: x.get("properties", {}).get("confidence_score", 0),
                                    reverse=True)
        
        for i, rel in enumerate(sorted_relationships[:15], 1):
            source_text = entity_text_map.get(rel["source"], rel["source"])
            target_text = entity_text_map.get(rel["target"], rel["target"])
            source_type = entity_type_map.get(rel["source"], "Unknown")
            target_type = entity_type_map.get(rel["target"], "Unknown")
            rel_name = rel.get("properties", {}).get("relationship_name", "UNKNOWN")
            confidence = rel.get("properties", {}).get("confidence_score", 0)
            extraction_method = rel.get("properties", {}).get("extraction_method", "unknown")
            
            print(f"  {i:2d}. {source_text} ({source_type}) --[{rel_name}]--> {target_text} ({target_type})")
            print(f"      신뢰도: {confidence:.2f}, 추출방법: {extraction_method}")
            
            if rel.get("properties", {}).get("pattern_based"):
                print(f"      패턴 기반: ✅")
            if rel.get("properties", {}).get("llm_extracted"):
                print(f"      LLM 추출: ✅")
            
            if rel.get("properties", {}).get("context_snippet"):
                context = rel["properties"]["context_snippet"][:80]
                print(f"      컨텍스트: \"{context}...\"")
            print()
    
    # 구조별 엔티티 분포 분석
    structure_entity_distribution = {}
    for entity in keyword_entities:
        source_structure = entity.get("properties", {}).get("source_structure", "unknown")
        if source_structure not in structure_entity_distribution:
            structure_entity_distribution[source_structure] = []
        structure_entity_distribution[source_structure].append(entity.get("properties", {}).get("text", ""))
    
    print(f"\n📊 구조별 엔티티 분포:")
    for structure_id, entities in structure_entity_distribution.items():
        # 구조 이름 찾기
        structure_name = "Unknown"
        for struct_entity in structure_entities:
            if struct_entity["id"] == structure_id:
                structure_name = struct_entity.get("properties", {}).get("title", structure_id)
                break
        
        print(f"  - {structure_name}: {len(entities)}개 엔티티")
        print(f"    {', '.join(entities[:5])}{'...' if len(entities) > 5 else ''}")
    
    # 결과를 파일로 저장
    output_file = "test/advanced_entity_relationships_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 전체 결과가 {output_file}에 저장되었습니다.")
    
    # 성공 여부 판단
    success = len(entity_relationships) > 0
    if success:
        print("🎉 테스트 성공! 엔티티 간 직접 관계가 성공적으로 추출되었습니다.")
    else:
        print("⚠️  테스트 주의: 엔티티 간 직접 관계가 추출되지 않았습니다.")
    
    return success

if __name__ == "__main__":
    test_advanced_entity_relationships()