#!/usr/bin/env python3
"""
Complete KG Pipeline Test
테스트 순서:
1. 구조 분석 (prerequisite)
2. LLM 서비스 초기화 확인
3. 계층적 KG 생성
4. 관계 필터링 결과 분석
"""

import sys
import os
sys.path.append('../backend')
os.chdir('../backend')

from services.hierarchical_kg_builder import HierarchicalKGBuilder
from services.local_file_analyzer import LocalFileAnalyzer
from db.database import get_db
import json

def main():
    # Database connection
    db = next(get_db())
    
    try:
        print('=== Complete KG Pipeline Test ===')
        
        # 1. Test structure analysis prerequisite
        analyzer = LocalFileAnalyzer(db)
        test_file = '../test/hierarchical_kg_test_document.md'
        
        with open(test_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        print(f'📄 분석 대상: {test_file} (길이: {len(text)}자)')
        
        # Force structure analysis
        structure_results = analyzer.analyze_document_structure(
            text=text,
            file_extension='.md'
        )
        print(f'📊 구조 분석 완료: {len(structure_results)} 구조 요소')
        
        # 2. Test KG builder with LLM service
        kg_builder = HierarchicalKGBuilder(db_session=db)
        print(f'🤖 LLM 서비스 초기화: {hasattr(kg_builder, "llm_service")}')
        
        if hasattr(kg_builder, 'llm_service'):
            print(f'🔗 Ollama 클라이언트: {hasattr(kg_builder.llm_service, "ollama_client")}')
            if hasattr(kg_builder.llm_service, 'ollama_client') and kg_builder.llm_service.ollama_client:
                print('✅ LLM 서비스가 정상적으로 초기화되었습니다')
            else:
                print('⚠️ LLM 서비스는 초기화되었지만 Ollama 클라이언트가 없습니다')
        
        # 3. Test KG generation
        print('\n🔨 KG 생성 시작...')
        kg_result = kg_builder.build_hierarchical_kg(
            document_text=text,
            file_path=test_file,
            file_info={'name': 'test.md', 'size': len(text)},
            structure_results=structure_results
        )
        
        # 4. Analyze results
        entities = kg_result['knowledge_graph']['entities']
        relationships = kg_result['knowledge_graph']['relationships']
        
        print(f'\n=== KG 생성 결과 ===')
        print(f'📦 엔티티 총 개수: {len(entities)}')
        print(f'🔗 관계 총 개수: {len(relationships)}')
        
        # Entity breakdown
        entity_types = {}
        hierarchical_entities = 0
        for entity in entities:
            entity_type = entity['type']
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
            if entity.get('properties', {}).get('hierarchical_entity'):
                hierarchical_entities += 1
        
        print(f'\n📊 엔티티 타입별 분류:')
        for entity_type, count in entity_types.items():
            print(f'  {entity_type}: {count}개')
        print(f'🏗️ 계층적 엔티티: {hierarchical_entities}개')
        
        # Relationship analysis
        relationship_types = {}
        entity_to_entity_relationships = 0
        inferred_relationships = 0
        
        for rel in relationships:
            rel_type = rel['type']
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
            if rel.get('properties', {}).get('entity_to_entity'):
                entity_to_entity_relationships += 1
            if rel.get('properties', {}).get('inferred'):
                inferred_relationships += 1
        
        print(f'\n🔗 관계 타입별 분류:')
        for rel_type, count in relationship_types.items():
            print(f'  {rel_type}: {count}개')
        print(f'🤝 엔티티간 관계: {entity_to_entity_relationships}개')
        print(f'🧠 추론된 관계: {inferred_relationships}개')
        
        # Check meaningful relationship filtering
        text_based_relationships = [r for r in relationships 
                                  if r.get('properties', {}).get('entity_to_entity') 
                                  and not r.get('properties', {}).get('inferred')]
        print(f'✨ 텍스트 기반 의미있는 관계: {len(text_based_relationships)}개')
        
        # Show sample meaningful relationships
        if text_based_relationships:
            print(f'\n🔍 의미있는 관계 샘플:')
            for rel in text_based_relationships[:3]:
                src_id = rel['source']
                tgt_id = rel['target']
                rel_name = rel['properties'].get('relationship_name', rel['type'])
                confidence = rel['properties'].get('confidence_score', 0)
                print(f'  {src_id} --[{rel_name}]--> {tgt_id} (신뢰도: {confidence:.3f})')
        
        # Save results for inspection
        with open('../tmp/kg_test_result.json', 'w', encoding='utf-8') as f:
            json.dump(kg_result, f, ensure_ascii=False, indent=2)
        print(f'\n💾 결과 저장: tmp/kg_test_result.json')
        
        print('\n✅ 전체 KG 파이프라인 테스트 완료!')
        
    except Exception as e:
        print(f'❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    main()