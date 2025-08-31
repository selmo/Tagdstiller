"""
Hierarchical Knowledge Graph Builder

문서 구조 정보를 기반으로 계층적 KG를 구축합니다.
문서 → 섹션 → 하위구조(테이블, 단락, 이미지) → 엔티티 관계를 명시합니다.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from .kg_schema_manager import KGSchemaManager, DocumentDomain
from .memgraph_service import MemgraphService


def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]


@dataclass
class StructuralElement:
    """문서 구조 요소"""
    id: str
    type: str  # Section, Table, Paragraph, Image, List, etc.
    properties: Dict[str, Any]
    parent_id: Optional[str] = None
    children: List[str] = None
    content: str = ""
    position: Dict[str, Any] = None  # page, line, bbox 등


@dataclass
class HierarchicalEntity:
    """계층적 엔티티 (구조 요소와 연결된 엔티티)"""
    id: str
    type: str
    properties: Dict[str, Any]
    source_structure: str  # 이 엔티티가 발견된 구조 요소 ID
    extraction_context: Dict[str, Any]  # 추출 컨텍스트 정보


class HierarchicalKGBuilder:
    """계층적 Knowledge Graph 빌더"""
    
    def __init__(self, memgraph_config: Dict[str, Any] = None, auto_save_to_memgraph: bool = True, db_session = None):
        self.schema_manager = KGSchemaManager()
        self.auto_save_to_memgraph = auto_save_to_memgraph
        self.logger = logging.getLogger(__name__)
        self.db_session = db_session
        
        # LLM 서비스 초기화 (관계 추출용)
        self.llm_service = None
        if db_session:
            try:
                from extractors.llm_extractor import LLMExtractor
                from services.config_service import ConfigService
                
                # LLM 설정 로드
                llm_config = {
                    'provider': 'ollama',
                    'model': ConfigService.get_config_value(db_session, 'OLLAMA_MODEL', 'llama3.2'),
                    'base_url': ConfigService.get_config_value(db_session, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
                    'timeout': ConfigService.get_int_config(db_session, 'OLLAMA_TIMEOUT', 30)
                }
                
                self.llm_service = LLMExtractor(config=llm_config, db_session=db_session)
                if self.llm_service.load_model():
                    self.logger.info("✅ 계층적 KG Builder: LLM 서비스 활성화")
                else:
                    self.logger.warning("⚠️ 계층적 KG Builder: LLM 서비스 로드 실패")
                    self.llm_service = None
            except Exception as e:
                self.logger.warning(f"⚠️ 계층적 KG Builder: LLM 서비스 초기화 실패 ({e})")
                self.llm_service = None
        
        # Memgraph 서비스 초기화
        self.memgraph_service = None
        if auto_save_to_memgraph:
            try:
                self.memgraph_service = MemgraphService(
                    uri=memgraph_config.get("uri", "bolt://localhost:7687") if memgraph_config else "bolt://localhost:7687",
                    username=memgraph_config.get("username", "") if memgraph_config else "",
                    password=memgraph_config.get("password", "") if memgraph_config else ""
                )
                
                if self.memgraph_service.is_connected():
                    self.logger.info("✅ 계층적 KG Builder: Memgraph 자동 저장 활성화")
                else:
                    self.logger.warning("⚠️ 계층적 KG Builder: Memgraph 연결 실패")
                    self.memgraph_service = None
            except Exception as e:
                self.logger.warning(f"⚠️ 계층적 KG Builder: Memgraph 초기화 실패 ({e})")
                self.memgraph_service = None
    
    def build_hierarchical_knowledge_graph(
        self, 
        file_path: str, 
        document_text: str, 
        keywords: Dict[str, Any], 
        metadata: Dict[str, Any], 
        structure_analysis: Dict[str, Any] = None, 
        parsing_results: Dict[str, Any] = None, 
        force_rebuild: bool = False
    ) -> Dict[str, Any]:
        """
        문서 구조를 기반으로 계층적 Knowledge Graph 구축
        
        Args:
            file_path: 문서 파일 경로
            document_text: 문서 텍스트
            keywords: 키워드 추출 결과
            metadata: 파일 메타데이터
            structure_analysis: 문서 구조 분석 결과
            parsing_results: 파싱 결과
            force_rebuild: 강제 재구축 여부
            
        Returns:
            계층적 KG 데이터
        """
        self.logger.info(f"🏗️ 계층적 KG 구축 시작: {file_path}")
        
        # 문서 텍스트를 인스턴스 변수로 저장 (관계 분석용)
        self._current_document_text = document_text
        
        # 도메인 감지
        domain, domain_confidence = self.schema_manager.detect_document_domain(document_text, metadata)
        
        result = {
            "entities": [],
            "relationships": [],
            "structural_hierarchy": [],
            "metadata": {
                "created_at": self._get_timestamp(),
                "file_path": file_path,
                "hierarchical_structure": True,
                "detected_domain": domain.value,
                "domain_confidence": domain_confidence,
                "extractors_used": list(keywords.keys()) if keywords else []
            }
        }
        
        # 1. 문서 루트 엔티티 생성
        doc_id = _hash(str(file_path))
        doc_entity = self._create_document_entity(doc_id, file_path, metadata, parsing_results, domain)
        result["entities"].append(doc_entity)
        
        # 2. 구조 요소 분석 및 엔티티 생성
        structural_elements = self._analyze_document_structure(
            doc_id, structure_analysis, parsing_results, domain
        )
        
        # 3. 구조 요소를 KG 엔티티로 변환
        structure_entities, structure_relationships = self._create_structure_entities_and_relationships(
            doc_id, structural_elements, domain
        )
        result["entities"].extend(structure_entities)
        result["relationships"].extend(structure_relationships)
        
        # 4. 키워드를 구조 요소별로 분류하고 엔티티화
        keyword_entities, keyword_relationships = self._create_hierarchical_keyword_entities(
            doc_id, keywords, structural_elements, document_text, domain
        )
        result["entities"].extend(keyword_entities)
        result["relationships"].extend(keyword_relationships)
        
        # 5. 엔티티 간 직접 관계 추출 **NEW!**
        entity_relationships = self._extract_entity_to_entity_relationships(
            result["entities"], document_text, domain, structural_elements
        )
        result["relationships"].extend(entity_relationships)
        
        # 6. 구조적 계층 정보 구축
        result["structural_hierarchy"] = self._build_structural_hierarchy(structural_elements)
        
        # 7. Memgraph에 자동 저장
        if self.memgraph_service and self.auto_save_to_memgraph:
            self._save_to_memgraph(result, file_path)
        
        self.logger.info(f"✅ 계층적 KG 구축 완료: {len(result['entities'])}개 엔티티, {len(result['relationships'])}개 관계")
        return result
    
    def _create_document_entity(self, doc_id: str, file_path: str, metadata: Dict[str, Any], 
                              parsing_results: Dict[str, Any], domain: DocumentDomain) -> Dict[str, Any]:
        """문서 루트 엔티티 생성"""
        return {
            "id": doc_id,
            "type": "Document",
            "properties": {
                "title": metadata.get("name", Path(file_path).name),
                "path": file_path,
                "domain": domain.value,
                "size": metadata.get("size"),
                "extension": metadata.get("extension"),
                "parser_count": len(parsing_results.get("parsing_results", {})) if parsing_results else 0,
                "best_parser": parsing_results.get("summary", {}).get("best_parser") if parsing_results else None,
                "hierarchical_root": True
            }
        }
    
    def _analyze_document_structure(self, doc_id: str, structure_analysis: Dict[str, Any], 
                                   parsing_results: Dict[str, Any], domain: DocumentDomain) -> List[StructuralElement]:
        """문서 구조 분석하여 구조 요소 목록 생성"""
        structural_elements = []
        
        # structure_analysis 형식 확인 및 변환
        if not structure_analysis:
            self.logger.warning("구조 분석 결과가 없음, 기본 구조 생성")
            return self._create_default_structure(doc_id)
        
        # local_analysis.py에서 오는 형식 처리: {"sections": [...], "tables_count": ...}
        if "sections" in structure_analysis:
            sections = structure_analysis.get("sections", [])
            if sections:
                self.logger.info(f"📊 구조 분석 결과 활용: {len(sections)}개 섹션 발견")
                # 섹션을 StructuralElement로 변환
                for i, section in enumerate(sections):
                    section_id = f"section_{doc_id}_{i}"
                    element = StructuralElement(
                        id=section_id,
                        type="Section",
                        properties={
                            "title": section.get("title", f"Section {i+1}"),
                            "level": section.get("level", 2),
                            "line": section.get("line"),
                            "parser": "local_analysis",
                            "index": i,
                            "number": section.get("number")
                        },
                        parent_id=doc_id,
                        content="",
                        position={"line": section.get("line")}
                    )
                    structural_elements.append(element)
                
                # 테이블 정보 처리
                tables_count = structure_analysis.get("tables_count", 0)
                if tables_count > 0:
                    table_id = f"table_{doc_id}_collection"
                    table_element = StructuralElement(
                        id=table_id,
                        type="Table",
                        properties={
                            "title": f"Tables ({tables_count})",
                            "count": tables_count,
                            "parser": "local_analysis",
                            "index": len(structural_elements)
                        },
                        parent_id=doc_id,
                        content="",
                        position={}
                    )
                    structural_elements.append(table_element)
                
                return structural_elements
        
        # 기존 형식 처리: {"structure_elements": [...], "summary": {...}}
        if not structure_analysis.get("structure_elements"):
            self.logger.warning("구조 분석 결과가 없음, 기본 구조 생성")
            return self._create_default_structure(doc_id)
        
        best_parser = structure_analysis.get("summary", {}).get("best_parser")
        if not best_parser:
            return structural_elements
        
        # 파서별 구조 정보에서 구조 요소 추출
        if best_parser in parsing_results.get("parsing_results", {}):
            parser_result = parsing_results["parsing_results"][best_parser]
            
            if "structured_info" in parser_result:
                structured_info = parser_result["structured_info"]
                structural_elements = self._extract_structural_elements_from_parser(
                    doc_id, best_parser, structured_info, domain
                )
        
        self.logger.info(f"📊 구조 요소 분석 완료: {len(structural_elements)}개 요소")
        return structural_elements
    
    def _extract_structural_elements_from_parser(self, doc_id: str, parser_name: str, 
                                               structured_info: Dict[str, Any], 
                                               domain: DocumentDomain) -> List[StructuralElement]:
        """파서 결과에서 구조 요소 추출"""
        elements = []
        
        # Document Structure 처리
        if "document_structure" in structured_info:
            doc_structure = structured_info["document_structure"]
            
            # 섹션 처리
            sections = doc_structure.get("sections", [])
            for i, section in enumerate(sections):
                section_id = f"section_{doc_id}_{i}"
                element = StructuralElement(
                    id=section_id,
                    type="Section",
                    properties={
                        "title": section.get("title", f"Section {i+1}"),
                        "level": section.get("level", 1),
                        "line": section.get("line"),
                        "parser": parser_name,
                        "index": i
                    },
                    parent_id=doc_id,
                    content=section.get("content", ""),
                    position={"line": section.get("line")}
                )
                elements.append(element)
            
            # 테이블 처리
            tables = doc_structure.get("tables", [])
            for i, table in enumerate(tables):
                table_id = f"table_{doc_id}_{i}"
                element = StructuralElement(
                    id=table_id,
                    type="Table",
                    properties={
                        "content": table.get("content", "")[:500],  # 테이블 내용 제한
                        "page": table.get("page"),
                        "parser": parser_name,
                        "index": i,
                        "row_count": len(table.get("rows", [])),
                        "column_count": len(table.get("columns", []))
                    },
                    parent_id=doc_id,
                    content=table.get("content", ""),
                    position={"page": table.get("page")}
                )
                elements.append(element)
            
            # 이미지 처리
            images = doc_structure.get("images", [])
            for i, image in enumerate(images):
                image_id = f"image_{doc_id}_{i}"
                element = StructuralElement(
                    id=image_id,
                    type="Image",
                    properties={
                        "caption": image.get("caption", ""),
                        "page": image.get("page"),
                        "parser": parser_name,
                        "index": i,
                        "width": image.get("width"),
                        "height": image.get("height")
                    },
                    parent_id=doc_id,
                    content=image.get("caption", ""),
                    position={"page": image.get("page")}
                )
                elements.append(element)
        
        # Docling 파서의 추가 구조 정보 처리
        if parser_name == "docling":
            elements.extend(self._extract_docling_specific_elements(doc_id, structured_info))
        
        return elements
    
    def _extract_docling_specific_elements(self, doc_id: str, structured_info: Dict[str, Any]) -> List[StructuralElement]:
        """Docling 파서 특화 구조 요소 추출"""
        elements = []
        
        # Docling의 상세 구조 정보 처리
        if "detailed_structure" in structured_info:
            detailed = structured_info["detailed_structure"]
            
            # 단락 처리
            paragraphs = detailed.get("paragraphs", [])
            for i, para in enumerate(paragraphs):
                para_id = f"paragraph_{doc_id}_{i}"
                element = StructuralElement(
                    id=para_id,
                    type="Paragraph",
                    properties={
                        "text": para.get("text", "")[:200],  # 단락 텍스트 제한
                        "page": para.get("page"),
                        "parser": "docling",
                        "index": i,
                        "word_count": len(para.get("text", "").split())
                    },
                    parent_id=doc_id,
                    content=para.get("text", ""),
                    position={"page": para.get("page")}
                )
                elements.append(element)
            
            # 목록 처리
            lists = detailed.get("lists", [])
            for i, list_item in enumerate(lists):
                list_id = f"list_{doc_id}_{i}"
                element = StructuralElement(
                    id=list_id,
                    type="List",
                    properties={
                        "items": list_item.get("items", [])[:10],  # 목록 항목 제한
                        "list_type": list_item.get("type", "unordered"),
                        "page": list_item.get("page"),
                        "parser": "docling",
                        "index": i,
                        "item_count": len(list_item.get("items", []))
                    },
                    parent_id=doc_id,
                    content="\n".join(list_item.get("items", [])),
                    position={"page": list_item.get("page")}
                )
                elements.append(element)
        
        return elements
    
    def _create_default_structure(self, doc_id: str) -> List[StructuralElement]:
        """기본 구조 요소 생성 (구조 분석 결과가 없을 때)"""
        return [
            StructuralElement(
                id=f"default_section_{doc_id}",
                type="Section",
                properties={
                    "title": "Default Section",
                    "level": 1,
                    "parser": "default",
                    "index": 0
                },
                parent_id=doc_id,
                content=""
            )
        ]
    
    def _create_structure_entities_and_relationships(self, doc_id: str, structural_elements: List[StructuralElement], 
                                                   domain: DocumentDomain) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """구조 요소를 KG 엔티티와 관계로 변환"""
        entities = []
        relationships = []
        
        for element in structural_elements:
            # 구조 엔티티 생성
            structure_entity = {
                "id": element.id,
                "type": element.type,
                "properties": {
                    **element.properties,
                    "domain": domain.value,
                    "structural_element": True,
                    "content_preview": element.content[:100] if element.content else "",
                    "has_content": bool(element.content)
                }
            }
            entities.append(structure_entity)
            
            # 부모-자식 관계 생성
            if element.parent_id:
                relationship = {
                    "source": element.parent_id,
                    "target": element.id,
                    "type": "CONTAINS_STRUCTURE",
                    "properties": {
                        "structure_type": element.type,
                        "relationship_name": f"CONTAINS_{element.type.upper()}",
                        "position_info": element.position or {},
                        "domain": domain.value
                    }
                }
                relationships.append(relationship)
        
        return entities, relationships
    
    def _create_hierarchical_keyword_entities(self, doc_id: str, keywords: Dict[str, Any], 
                                            structural_elements: List[StructuralElement], 
                                            document_text: str, domain: DocumentDomain) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """키워드를 구조 요소별로 분류하여 계층적 엔티티 생성"""
        entities = []
        relationships = []
        domain_schema = self.schema_manager.get_domain_schema(domain)
        
        # 구조 요소별 컨텍스트 매핑 생성
        structure_contexts = self._build_structure_context_map(structural_elements, document_text)
        
        for extractor_name, extractor_keywords in keywords.items():
            for kw_data in extractor_keywords:
                keyword = kw_data.get("keyword", "")
                if not keyword or len(keyword) < 2:
                    continue
                
                # 키워드를 단어 중심으로 분해
                word_keywords = self._extract_words_from_keyword(keyword)
                
                for word_keyword in word_keywords:
                    if len(word_keyword) < 2:
                        continue
                    
                    # 이 키워드가 속한 구조 요소 찾기
                    containing_structures = self._find_containing_structures(
                        word_keyword, structure_contexts, kw_data
                    )
                    
                    # 도메인별 엔티티 타입 결정
                    entity_type = self.schema_manager._classify_keyword_to_entity_type(
                        word_keyword, domain_schema["entities"]
                    )
                    
                    # 각 구조 요소별로 키워드 엔티티 생성
                    for structure_id, context_info in containing_structures:
                        # 고유 ID 생성 (키워드 + 구조 요소 + 추출기)
                        kw_entity_id = f"{entity_type.lower()}_{_hash(word_keyword)}_{_hash(structure_id)}_{extractor_name}"
                        
                        # 추가 속성 생성
                        additional_props = self.schema_manager._get_additional_entity_properties(
                            word_keyword, entity_type, domain
                        )
                        
                        # 키워드 엔티티 생성
                        keyword_entity = {
                            "id": kw_entity_id,
                            "type": entity_type,
                            "properties": {
                                "text": word_keyword,
                                "domain": domain.value,
                                "source_structure": structure_id,
                                "source_structure_type": context_info.get("structure_type"),
                                "extractor": extractor_name,
                                "score": kw_data.get("score", 0),
                                "category": kw_data.get("category", "unknown"),
                                "extraction_context": context_info,
                                "hierarchical_entity": True,
                                **additional_props
                            }
                        }
                        entities.append(keyword_entity)
                        
                        # 구조 요소 → 키워드 엔티티 관계
                        context_snippet = context_info.get("context", "")
                        base_rel_type, specific_rel_type = self.schema_manager.get_enhanced_relationship_type(
                            context_info.get("structure_type", "Structure"), entity_type, context_snippet, domain
                        )
                        
                        structure_relationship = {
                            "source": structure_id,
                            "target": kw_entity_id,
                            "type": base_rel_type,
                            "properties": {
                                "relationship_name": specific_rel_type,
                                "extraction_method": extractor_name,
                                "confidence_score": kw_data.get("score", 0),
                                "context_snippet": context_snippet[:100],
                                "domain": domain.value,
                                "hierarchical_relationship": True
                            }
                        }
                        relationships.append(structure_relationship)
        
        self.logger.info(f"🔗 계층적 키워드 엔티티 생성: {len(entities)}개 엔티티, {len(relationships)}개 관계")
        return entities, relationships
    
    def _build_structure_context_map(self, structural_elements: List[StructuralElement], 
                                   document_text: str) -> Dict[str, Dict[str, Any]]:
        """구조 요소별 컨텍스트 매핑 생성"""
        context_map = {}
        
        for element in structural_elements:
            context_map[element.id] = {
                "structure_type": element.type,
                "content": element.content,
                "properties": element.properties,
                "position": element.position or {},
                "context": element.content[:200] if element.content else ""
            }
        
        return context_map
    
    def _find_containing_structures(self, keyword: str, structure_contexts: Dict[str, Dict[str, Any]], 
                                  kw_data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """키워드가 포함된 구조 요소들 찾기"""
        containing_structures = []
        keyword_lower = keyword.lower()
        
        # 키워드 위치 정보가 있는 경우 정확한 매핑
        if kw_data.get("start_position") is not None:
            # TODO: 위치 기반 정확한 구조 매핑 구현
            pass
        
        # 컨텍스트 기반 매칭
        for structure_id, context_info in structure_contexts.items():
            content = context_info.get("content", "").lower()
            if keyword_lower in content:
                containing_structures.append((structure_id, context_info))
        
        # 매칭되는 구조가 없으면 기본 구조에 할당
        if not containing_structures and structure_contexts:
            default_structure = list(structure_contexts.items())[0]
            containing_structures.append(default_structure)
        
        return containing_structures
    
    def _extract_words_from_keyword(self, keyword: str) -> List[str]:
        """키워드에서 의미있는 단어들 추출"""
        import re
        
        # 단순한 경우는 그대로 반환
        if len(keyword.split()) <= 2:
            cleaned = self._remove_korean_particles(keyword.strip())
            return [cleaned] if cleaned else []
        
        # 복잡한 키워드는 단어별로 분해
        words = []
        raw_words = re.split(r'[^\w가-힣]+', keyword)
        
        for word in raw_words:
            word = word.strip()
            if len(word) >= 2:
                cleaned_word = self._remove_korean_particles(word)
                if cleaned_word and not self._is_stop_word(cleaned_word):
                    words.append(cleaned_word)
        
        return words if words else [self._remove_korean_particles(keyword.strip())]
    
    def _remove_korean_particles(self, word: str) -> str:
        """한국어 조사 제거"""
        if not word:
            return word
        
        particles = [
            '이', '가', '을', '를', '의', '에', '에서', '에게', '한테', '으로', '로',
            '와', '과', '하고', '이랑', '랑', '아', '야', '이여', '여',
            '은', '는', '도', '만', '까지', '부터', '조차', '마저', '밖에', '뿐'
        ]
        
        particles.sort(key=len, reverse=True)
        original_word = word
        
        for particle in particles:
            if word.endswith(particle) and len(word) > len(particle):
                candidate = word[:-len(particle)]
                if len(candidate) >= 2:
                    word = candidate
                    break
        
        return word if len(word) >= 2 else (original_word if len(original_word) >= 2 else "")
    
    def _is_stop_word(self, word: str) -> bool:
        """불용어 확인"""
        korean_stops = {'이다', '있다', '없다', '되다', '하다', '그것', '것이'}
        english_stops = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        return word.lower() in korean_stops or word.lower() in english_stops
    
    def _build_structural_hierarchy(self, structural_elements: List[StructuralElement]) -> List[Dict[str, Any]]:
        """구조적 계층 정보 구축"""
        hierarchy = []
        
        for element in structural_elements:
            hierarchy_item = {
                "id": element.id,
                "type": element.type,
                "parent_id": element.parent_id,
                "children": element.children or [],
                "level": self._calculate_hierarchy_level(element, structural_elements),
                "properties": element.properties
            }
            hierarchy.append(hierarchy_item)
        
        return sorted(hierarchy, key=lambda x: (x.get("level", 0), x.get("id", "")))
    
    def _calculate_hierarchy_level(self, element: StructuralElement, all_elements: List[StructuralElement]) -> int:
        """구조 요소의 계층 레벨 계산"""
        level = 0
        current_parent = element.parent_id
        
        while current_parent:
            level += 1
            parent_element = next((e for e in all_elements if e.id == current_parent), None)
            if parent_element:
                current_parent = parent_element.parent_id
            else:
                break
        
        return level
    
    def _save_to_memgraph(self, result: Dict[str, Any], file_path: str):
        """Memgraph에 계층적 KG 데이터 저장"""
        try:
            self.logger.info(f"💾 계층적 KG를 Memgraph에 저장 중: {file_path}")
            
            success = self.memgraph_service.insert_kg_data(result, clear_existing=True)
            if success:
                result["metadata"]["memgraph_saved"] = True
                result["metadata"]["memgraph_saved_at"] = self._get_timestamp()
                self.logger.info(f"✅ 계층적 KG Memgraph 저장 완료: {file_path}")
            else:
                result["metadata"]["memgraph_saved"] = False
                self.logger.warning(f"⚠️ 계층적 KG Memgraph 저장 실패: {file_path}")
        except Exception as e:
            self.logger.error(f"❌ 계층적 KG Memgraph 저장 오류: {e}")
            result["metadata"]["memgraph_saved"] = False
            result["metadata"]["memgraph_error"] = str(e)
    
    def _extract_entity_to_entity_relationships(self, entities: List[Dict[str, Any]], document_text: str, 
                                              domain: DocumentDomain, structural_elements: List[StructuralElement]) -> List[Dict[str, Any]]:
        """엔티티 간 직접 관계 추출"""
        relationships = []
        
        # hierarchical_entity=True인 키워드 엔티티만 필터링
        keyword_entities = [
            entity for entity in entities 
            if entity.get("properties", {}).get("hierarchical_entity") == True
        ]
        
        if len(keyword_entities) < 2:
            self.logger.info("🔗 엔티티 관계 추출: 관계를 형성할 엔티티가 부족합니다")
            return relationships
        
        self.logger.info(f"🔗 엔티티 간 관계 추출 시작: {len(keyword_entities)}개 엔티티 분석")
        
        # 1. 동일 구조 내 엔티티 페어 찾기
        structure_entity_pairs = self._find_structure_based_entity_pairs(keyword_entities)
        
        # 2. 각 페어에 대해 관계 추론
        for entity1, entity2, shared_context in structure_entity_pairs:
            relationship = self._infer_entity_relationship(entity1, entity2, shared_context, domain)
            if relationship:
                relationships.append(relationship)
        
        # 3. 도메인별 특수 관계 추론
        domain_relationships = self._infer_domain_specific_relationships(keyword_entities, domain, document_text)
        relationships.extend(domain_relationships)
        
        # 4. LLM 기반 고급 관계 추론 (선택적)
        llm_relationships = self._llm_based_relationship_extraction(keyword_entities, document_text, domain)
        relationships.extend(llm_relationships)
        
        self.logger.info(f"✅ 엔티티 관계 추출 완료: {len(relationships)}개 직접 관계 발견")
        return relationships
    
    def _find_structure_based_entity_pairs(self, keyword_entities: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]]:
        """구조 기반 엔티티 페어 찾기 - 의미있는 관계만 선택"""
        entity_pairs = []
        
        # 구조별로 엔티티 그룹화
        structure_entities = {}
        for entity in keyword_entities:
            source_structure = entity.get("properties", {}).get("source_structure")
            if source_structure:
                if source_structure not in structure_entities:
                    structure_entities[source_structure] = []
                structure_entities[source_structure].append(entity)
        
        # 각 구조 내에서 의미있는 엔티티 페어만 생성
        for structure_id, entities in structure_entities.items():
            if len(entities) < 2:
                continue
            
            # 엔티티를 타입별로 그룹화
            entities_by_type = {}
            for entity in entities:
                entity_type = entity.get("type", "Unknown")
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity)
            
            # 의미있는 관계 패턴만 선택적으로 페어링
            meaningful_pairs = self._select_meaningful_pairs(entities_by_type, structure_id)
            entity_pairs.extend(meaningful_pairs)
        
        self.logger.info(f"🔍 구조 기반 엔티티 페어 발견: {len(entity_pairs)}개")
        return entity_pairs
    
    def _select_meaningful_pairs(self, entities_by_type: Dict[str, List[Dict]], structure_id: str) -> List[Tuple]:
        """의미있는 엔티티 페어만 선택 - 문서에서 실제 언급된 관계만"""
        pairs = []
        
        # 모든 엔티티 목록
        all_entities = []
        for entities in entities_by_type.values():
            all_entities.extend(entities)
        
        # 문서 텍스트에서 실제로 언급된 관계만 찾기
        for i, entity1 in enumerate(all_entities):
            for j, entity2 in enumerate(all_entities):
                if i >= j:  # 중복 방지
                    continue
                
                # 문서에서 실제 관계가 언급되었는지 확인
                if self._check_actual_relationship_in_text(entity1, entity2):
                    shared_context = {
                        "structure_id": structure_id,
                        "structure_type": entity1.get("properties", {}).get("source_structure_type"),
                        "context": self._find_relationship_context(entity1, entity2),
                        "extractor": entity1.get("properties", {}).get("extractor")
                    }
                    pairs.append((entity1, entity2, shared_context))
        
        return pairs
    
    def _check_actual_relationship_in_text(self, entity1: Dict, entity2: Dict) -> bool:
        """문서에서 두 엔티티 간 실제 관계가 언급되었는지 확인"""
        text1 = entity1.get("properties", {}).get("text", "").lower()
        text2 = entity2.get("properties", {}).get("text", "").lower()
        
        # 두 엔티티가 가까운 거리에 함께 언급되었는지 확인
        return self._are_entities_mentioned_together(text1, text2)
    
    def _are_entities_mentioned_together(self, entity1_text: str, entity2_text: str) -> bool:
        """두 엔티티가 문서에서 가까운 거리에 함께 언급되었는지 확인"""
        # 원본 문서 텍스트 가져오기 (self에 저장된 텍스트 사용)
        if not hasattr(self, '_current_document_text'):
            return False
        
        doc_text = self._current_document_text.lower()
        
        # 두 엔티티 위치 찾기
        entity1_positions = []
        entity2_positions = []
        
        # entity1 모든 위치 찾기
        start = 0
        while True:
            pos = doc_text.find(entity1_text, start)
            if pos == -1:
                break
            entity1_positions.append(pos)
            start = pos + 1
        
        # entity2 모든 위치 찾기
        start = 0
        while True:
            pos = doc_text.find(entity2_text, start)
            if pos == -1:
                break
            entity2_positions.append(pos)
            start = pos + 1
        
        # 더 엄격한 기준: 같은 문장이나 단락에서 언급 (100문자 이내)
        proximity_threshold = 100
        
        for pos1 in entity1_positions:
            for pos2 in entity2_positions:
                distance = abs(pos1 - pos2)
                if distance <= proximity_threshold:
                    # 추가 검증: 같은 문장이나 목록에 있는지 확인
                    if self._are_in_same_context_unit(pos1, pos2, doc_text):
                        return True
        
        return False
    
    def _are_in_same_context_unit(self, pos1: int, pos2: int, text: str) -> bool:
        """두 위치가 같은 컨텍스트 단위(문장, 목록 항목)에 있는지 확인"""
        # 두 위치 사이의 텍스트 추출
        start_pos = min(pos1, pos2)
        end_pos = max(pos1, pos2)
        between_text = text[start_pos:end_pos]
        
        # 문장 구분자나 목록 구분자가 있으면 다른 컨텍스트
        separators = ['\n\n', '. ', '.\n', '|', '- **', '### ', '## ']
        
        for separator in separators:
            if separator in between_text:
                return False
        
        return True
    
    def _find_relationship_context(self, entity1: Dict, entity2: Dict) -> str:
        """두 엔티티 간 관계의 문서 컨텍스트 찾기"""
        if not hasattr(self, '_current_document_text'):
            return ""
        
        text1 = entity1.get("properties", {}).get("text", "")
        text2 = entity2.get("properties", {}).get("text", "")
        doc_text = self._current_document_text
        
        # 문서에서 두 엔티티가 가장 가까이 언급된 위치 찾기
        min_distance = float('inf')
        best_context = ""
        
        # 각 엔티티의 모든 언급 위치 찾기
        positions1 = self._find_all_positions(doc_text.lower(), text1.lower())
        positions2 = self._find_all_positions(doc_text.lower(), text2.lower())
        
        # 가장 가까운 위치 조합 찾기
        for pos1 in positions1:
            for pos2 in positions2:
                distance = abs(pos1 - pos2)
                if distance < min_distance:
                    min_distance = distance
                    # 두 엔티티를 포함하는 컨텍스트 추출
                    start_pos = max(0, min(pos1, pos2) - 100)
                    end_pos = min(len(doc_text), max(pos1 + len(text1), pos2 + len(text2)) + 100)
                    best_context = doc_text[start_pos:end_pos].strip()
        
        return best_context[:200] + "..." if len(best_context) > 200 else best_context
    
    def _find_all_positions(self, text: str, keyword: str) -> List[int]:
        """텍스트에서 키워드의 모든 위치 찾기"""
        positions = []
        start = 0
        while True:
            pos = text.find(keyword, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
    
    def _are_complementary_technologies(self, tech1: Dict, tech2: Dict) -> bool:
        """두 기술이 보완적 관계인지 확인"""
        text1 = tech1.get("properties", {}).get("text", "").lower()
        text2 = tech2.get("properties", {}).get("text", "").lower()
        
        # 보완적 기술 패턴
        complementary_patterns = [
            ("fastapi", "sqlalchemy"),     # 웹 프레임워크와 ORM
            ("redis", "postgresql"),        # 캐시와 주 데이터베이스
            ("elasticsearch", "postgresql"), # 검색 엔진과 주 데이터베이스
            ("fastapi", "pydantic"),        # 웹 프레임워크와 검증 라이브러리
        ]
        
        for pattern1, pattern2 in complementary_patterns:
            if (pattern1 in text1 and pattern2 in text2) or (pattern2 in text1 and pattern1 in text2):
                return True
        
        return False
    
    def _infer_entity_relationship(self, entity1: Dict[str, Any], entity2: Dict[str, Any], 
                                 shared_context: Dict[str, Any], domain: DocumentDomain) -> Optional[Dict[str, Any]]:
        """두 엔티티 간의 관계 추론 - 의미있는 관계만"""
        type1 = entity1.get("type")
        type2 = entity2.get("type")
        text1 = entity1.get("properties", {}).get("text", "")
        text2 = entity2.get("properties", {}).get("text", "")
        
        if not all([type1, type2, text1, text2]):
            return None
        
        # 도메인별 관계 규칙 적용
        relationship_type = self._get_domain_relationship_type(type1, type2, text1, text2, domain, shared_context)
        
        # 관계가 없거나 너무 일반적인 경우 필터링
        if not relationship_type or relationship_type == "ASSOCIATED_WITH":
            return None
        
        # 신뢰도 점수 계산
        confidence_score = self._calculate_relationship_confidence(
            entity1, entity2, relationship_type, shared_context
        )
        
        # 낮은 신뢰도 관계 필터링 (임계값: 0.5)
        if confidence_score < 0.5:
            return None
        
        return {
            "source": entity1["id"],
            "target": entity2["id"], 
            "type": "RELATED_TO",
            "properties": {
                "relationship_name": relationship_type,
                "domain": domain.value,
                "context_snippet": shared_context.get("context", "")[:100],
                "extraction_method": shared_context.get("extractor"),
                "confidence_score": confidence_score,
                "entity_to_entity": True,
                "inferred": True
            }
        }
    
    def _calculate_relationship_confidence(self, entity1: Dict, entity2: Dict, 
                                         relationship_type: str, context: Dict) -> float:
        """관계 신뢰도 점수 계산"""
        # 기본 점수: 두 엔티티의 최소 점수
        base_score = min(
            entity1.get("properties", {}).get("score", 0),
            entity2.get("properties", {}).get("score", 0)
        )
        
        # 관계 타입별 가중치
        relationship_weights = {
            "USES": 0.9,
            "INTEGRATES_WITH": 0.85,
            "IMPLEMENTS": 0.8,
            "CONNECTS_TO": 0.8,
            "COMPLEMENTS": 0.75,
            "SUPPORTS": 0.7,
            "RELATED_TO": 0.5,  # 일반적 관계는 낮은 가중치
        }
        
        weight = relationship_weights.get(relationship_type, 0.6)
        
        # 컨텍스트 보너스 (컨텍스트가 있으면 점수 증가)
        context_bonus = 0.1 if context.get("context") else 0
        
        return min(base_score * weight + context_bonus, 1.0)
    
    def _get_domain_relationship_type(self, type1: str, type2: str, text1: str, text2: str, 
                                    domain: DocumentDomain, context: Dict[str, Any]) -> Optional[str]:
        """도메인별 관계 타입 결정"""
        
        # 기술 도메인 관계 규칙 - 의미있는 관계만
        if domain == DocumentDomain.TECHNICAL:
            # 특정 타입 간 직접적인 관계만 허용
            tech_rules = {
                ("Technology", "Database"): "USES",
                ("Framework", "Database"): "CONNECTS_TO", 
                ("Technology", "Framework"): "INTEGRATES_WITH",
                ("API", "Database"): "ACCESSES",
                ("Service", "Technology"): "IMPLEMENTS",
                ("Tool", "Framework"): "SUPPORTS"
            }
            
            # 양방향 확인
            direct = tech_rules.get((type1, type2))
            if direct:
                return direct
            
            reverse = tech_rules.get((type2, type1))
            if reverse:
                # 역방향 관계 매핑
                reverse_mapping = {
                    "USES": "USED_BY",
                    "CONNECTS_TO": "CONNECTED_BY", 
                    "INTEGRATES_WITH": "INTEGRATED_BY",
                    "ACCESSES": "ACCESSED_BY",
                    "IMPLEMENTS": "IMPLEMENTED_BY",
                    "SUPPORTS": "SUPPORTED_BY"
                }
                return reverse_mapping.get(reverse, reverse)
            
            # 명시적으로 정의되지 않은 관계는 None 반환
            return None
        
        # 학술 도메인 관계 규칙
        elif domain == DocumentDomain.ACADEMIC:
            academic_rules = {
                ("Author", "Research_Method"): "USES",
                ("Theory", "Research_Method"): "APPLIED_BY",
                ("Concept", "Theory"): "RELATED_TO",
                ("Dataset", "Research_Method"): "ANALYZED_BY"
            }
            
            return academic_rules.get((type1, type2)) or academic_rules.get((type2, type1))
        
        # 비즈니스 도메인 관계 규칙  
        elif domain == DocumentDomain.BUSINESS:
            business_rules = {
                ("Company", "Product"): "PRODUCES",
                ("Strategy", "Goal"): "ACHIEVES",
                ("Process", "Tool"): "UTILIZES"
            }
            
            return business_rules.get((type1, type2)) or business_rules.get((type2, type1))
        
        # 기본 관계 (컨텍스트 기반)
        context_text = context.get("context", "").lower()
        
        # 컨텍스트에서 관계 힌트 찾기
        if any(word in context_text for word in ["사용", "활용", "이용"]):
            return "USES"
        elif any(word in context_text for word in ["연결", "연동", "통합"]):
            return "INTEGRATES_WITH" 
        elif any(word in context_text for word in ["구현", "개발"]):
            return "IMPLEMENTS"
        elif any(word in context_text for word in ["지원", "도구"]):
            return "SUPPORTS"
        
        return "ASSOCIATED_WITH"  # 기본 관계
    
    def _infer_domain_specific_relationships(self, keyword_entities: List[Dict[str, Any]], 
                                           domain: DocumentDomain, document_text: str) -> List[Dict[str, Any]]:
        """도메인별 특수 관계 추론"""
        relationships = []
        
        if domain == DocumentDomain.TECHNICAL:
            # 기술 스택 관계 추론
            tech_entities = [e for e in keyword_entities if e.get("type") in ["Technology", "Framework", "Database", "Tool"]]
            
            # 잘 알려진 기술 조합 패턴
            known_patterns = [
                (["FastAPI", "SQLAlchemy"], "INTEGRATES_WITH"),
                (["React", "Node.js"], "WORKS_WITH"),
                (["PostgreSQL", "Redis"], "COMPLEMENTS"),
                (["Docker", "Kubernetes"], "ORCHESTRATED_BY")
            ]
            
            for pattern, rel_type in known_patterns:
                entities_in_pattern = []
                for entity in tech_entities:
                    entity_text = entity.get("properties", {}).get("text", "")
                    if any(pattern_item.lower() in entity_text.lower() for pattern_item in pattern):
                        entities_in_pattern.append(entity)
                
                # 패턴에 맞는 엔티티들 간 관계 생성
                for i in range(len(entities_in_pattern)):
                    for j in range(i + 1, len(entities_in_pattern)):
                        relationship = {
                            "source": entities_in_pattern[i]["id"],
                            "target": entities_in_pattern[j]["id"],
                            "type": "RELATED_TO",
                            "properties": {
                                "relationship_name": rel_type,
                                "domain": domain.value,
                                "pattern_based": True,
                                "confidence_score": 0.8,
                                "entity_to_entity": True,
                                "inferred": True
                            }
                        }
                        relationships.append(relationship)
        
        return relationships
    
    def _llm_based_relationship_extraction(self, keyword_entities: List[Dict[str, Any]], 
                                         document_text: str, domain: DocumentDomain) -> List[Dict[str, Any]]:
        """LLM 기반 엔티티 관계 추출"""
        relationships = []
        
        if not self.llm_service or not self.llm_service.is_loaded:
            self.logger.info("🤖 LLM 서비스가 없어 LLM 기반 관계 추출을 건너뜁니다")
            return relationships
        
        self.logger.info(f"🤖 LLM 기반 엔티티 관계 추출 시작")
        
        entity_map = {e['id']: e for e in keyword_entities}
        
        # 1. 엔티티가 언급된 컨텍스트(문장) 추출
        entity_contexts = self._get_entity_contexts(keyword_entities, document_text)
        
        # 2. 컨텍스트를 기반으로 관계 추출 프롬프트 생성
        prompt = self._create_relationship_extraction_prompt(entity_contexts, domain)
        
        if not prompt:
            self.logger.info("🤖 관계를 추출할 컨텍스트가 부족하여 LLM 호출을 건너뜁니다.")
            return relationships
            
        try:
            if hasattr(self.llm_service, 'ollama_client') and self.llm_service.ollama_client:
                llm_response = self.llm_service.ollama_client.invoke(prompt)
                
                if llm_response:
                    parsed_relationships = self._parse_llm_relationship_response(
                        llm_response, entity_map, domain
                    )
                    relationships.extend(parsed_relationships)
                    self.logger.info(f"🤖 LLM이 {len(parsed_relationships)}개의 엔티티 관계를 추출했습니다")
            else:
                self.logger.warning("🤖 LLM 클라이언트를 사용할 수 없습니다")
            
        except Exception as e:
            self.logger.warning(f"🤖 LLM 기반 관계 추출 중 오류: {e}")
        
        return relationships

    def _get_entity_contexts(self, entities: List[Dict[str, Any]], document_text: str, window_size: int = 1) -> Dict[str, Any]:
        """문서에서 엔티티가 언급된 문장(컨텍스트)을 찾습니다."""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', document_text)
        
        entity_contexts = {"entities": {}, "contexts": []}
        
        for entity in entities:
            text = entity.get("properties", {}).get("text", "")
            if text:
                entity_contexts["entities"][text] = {"id": entity["id"], "type": entity["type"]}

        for i, sentence in enumerate(sentences):
            found_entities = []
            for entity_text in entity_contexts["entities"].keys():
                if re.search(r'\b' + re.escape(entity_text) + r'\b', sentence, re.IGNORECASE):
                    found_entities.append(entity_text)
            
            if len(found_entities) > 1:
                context_sentences = sentences[max(0, i - window_size) : i + window_size + 1]
                context = " ".join(context_sentences).strip()
                entity_info = {
                    "entities": found_entities,
                    "context": context
                }
                entity_contexts["contexts"].append(entity_info)

        return entity_contexts

    def _create_relationship_extraction_prompt(self, entity_contexts: Dict[str, Any], domain: DocumentDomain) -> Optional[str]:
        """관계 추출을 위한 개선된 LLM 프롬프트 생성"""
        
        if not entity_contexts["contexts"]:
            return None

        domain_info = self.schema_manager.get_domain_schema(domain)
        relationship_types = ", ".join(domain_info.get("relationships", ["RELATED_TO"]))

        prompt_parts = [
            "Please analyze the relationships between the following entities based on the provided contexts from a document.",
            "The domain of the document is '{domain.value}'.",
            "\n**Instructions**:",
            "1. For each context, identify the relationship between the mentioned entities.",
            "2. The relationship must be one of the following types: {relationship_types}, or RELATED_TO if none apply.",
            "3. Format the output as a JSON array of objects, where each object has 'entity1', 'entity2', 'relationship', 'confidence' (from 0.0 to 1.0), and 'evidence' (the sentence supporting the relationship).",
            "4. Only extract relationships that are clearly and directly stated in the context. Do not infer relationships.",
            "\n**Contexts & Entities**:"]

        for item in entity_contexts["contexts"]:
            context_str = f"\n- **Context**: \"{item['context']}\""
            entities_str = f"  **Entities**: {', '.join(item['entities'])}"
            prompt_parts.append(context_str)
            prompt_parts.append(entities_str)

        prompt_parts.append("\n**Output (JSON Array)**:")
        
        return "\n".join(prompt_parts)

    def _parse_llm_relationship_response(self, llm_response: str, entity_map: Dict[str, Dict[str, Any]], 
                                       domain: DocumentDomain) -> List[Dict[str, Any]]:
        """LLM 응답(JSON)에서 관계 정보 파싱"""
        relationships = []
        try:
            # Find the JSON part of the response
            from typing import re
            json_match = re.search(r'\[(.*?)(\s*,?.*)*\]', llm_response, re.DOTALL)
            if not json_match:
                self.logger.warning("LLM 응답에서 JSON 배열을 찾을 수 없습니다.")
                return relationships

            parsed_json = json.loads(json_match.group(0))
            
            for rel in parsed_json:
                entity1_text = rel.get("entity1")
                entity2_text = rel.get("entity2")
                relationship_type = rel.get("relationship")
                confidence = rel.get("confidence")
                evidence = rel.get("evidence")

                # Find the full entity from the entity map
                entity1 = next((e for e in entity_map.values() if e['properties']['text'] == entity1_text), None)
                entity2 = next((e for e in entity_map.values() if e['properties']['text'] == entity2_text), None)

                if entity1 and entity2 and entity1["id"] != entity2["id"]:
                    relationship = {
                        "source": entity1["id"],
                        "target": entity2["id"],
                        "type": "RELATED_TO",
                        "properties": {
                            "relationship_name": relationship_type,
                            "domain": domain.value,
                            "extraction_method": "llm",
                            "confidence_score": confidence,
                            "context_snippet": evidence,
                            "entity_to_entity": True,
                            "inferred": True,
                            "llm_extracted": True
                        }
                    }
                    relationships.append(relationship)
        except json.JSONDecodeError as e:
            self.logger.warning(f"LLM 응답 JSON 파싱 오류: {e}")
        except Exception as e:
            self.logger.warning(f"LLM 응답 처리 중 오류: {e}")
            
        return relationships
    
    def _get_timestamp(self) -> str:
        """현재 타임스탬프 생성"""
        return datetime.now().isoformat()


def create_hierarchical_kg_builder(memgraph_config: Dict[str, Any] = None) -> HierarchicalKGBuilder:
    """계층적 KG 빌더 인스턴스 생성"""
    return HierarchicalKGBuilder(memgraph_config, auto_save_to_memgraph=True)