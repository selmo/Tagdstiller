"""
Knowledge Graph Builder Service

문서 전체를 Knowledge Graph로 변환하는 전용 서비스
LLM을 사용하여 엔티티와 관계를 추출하고 그래프 구조로 변환합니다.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from prompts.templates import KnowledgeGraphPrompts, PromptTemplate
from services.local_file_analyzer import LocalFileAnalyzer

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    """문서를 Knowledge Graph로 변환하는 빌더 클래스"""

    def __init__(self, db: Session):
        self.db = db
        self.analyzer = LocalFileAnalyzer(db)
        self.logger = logging.getLogger(__name__)

    def build_knowledge_graph(
        self,
        text: str,
        file_path: str,
        domain: str = "general",
        structure_info: Optional[Dict[str, Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        문서 텍스트에서 Knowledge Graph 생성

        Args:
            text: 문서 텍스트
            file_path: 파일 경로
            domain: 문서 도메인 (general, technical, academic, business, legal)
            structure_info: 문서 구조 정보 (선택)
            llm_config: LLM 설정 (선택)

        Returns:
            Knowledge Graph JSON 구조
        """
        try:
            self.logger.info(f"🔍 Knowledge Graph 생성 시작: {Path(file_path).name} (도메인: {domain})")

            # 1. 도메인별 프롬프트 선택
            prompt_template = self._get_kg_prompt_template(domain)

            # 2. 구조 정보 간략화
            structure_summary = self._summarize_structure(structure_info) if structure_info else "구조 정보 없음"

            # 3. 프롬프트 생성
            prompt = prompt_template.format(
                text=text[:100000],  # 최대 100K 문자 (약 50K 토큰)
                domain=domain,
                structure_info=structure_summary
            )

            # 4. LLM 호출 (LocalFileAnalyzer의 LLM 기능 활용)
            llm_response = self._call_llm_for_kg(prompt, llm_config or {})

            if not llm_response.get("success"):
                return self._create_error_result(llm_response.get("error", "LLM 호출 실패"))

            # 5. LLM 응답 파싱
            kg_data = self._parse_kg_response(llm_response.get("response", ""))

            # 6. 메타데이터 추가
            kg_result = self._enrich_kg_with_metadata(
                kg_data,
                file_path,
                domain,
                structure_info
            )

            self.logger.info(
                f"✅ Knowledge Graph 생성 완료: "
                f"{kg_result['stats']['entity_count']}개 엔티티, "
                f"{kg_result['stats']['relationship_count']}개 관계"
            )

            return kg_result

        except Exception as e:
            self.logger.error(f"❌ Knowledge Graph 생성 실패: {e}", exc_info=True)
            return self._create_error_result(str(e))

    def _get_kg_prompt_template(self, domain: str) -> PromptTemplate:
        """도메인별 KG 추출 프롬프트 선택"""
        domain_prompts = {
            "general": KnowledgeGraphPrompts.GENERAL_KG_EXTRAION,
            "technical": KnowledgeGraphPrompts.TECHNICAL_KG_EXTRACTION,
            "academic": KnowledgeGraphPrompts.ACADEMIC_KG_EXTRACTION,
            "business": KnowledgeGraphPrompts.BUSINESS_KG_EXTRACTION,
            "legal": KnowledgeGraphPrompts.LEGAL_KG_EXTRACTION,
        }
        return domain_prompts.get(domain, KnowledgeGraphPrompts.GENERAL_KG_EXTRAION)

    def _summarize_structure(self, structure_info: Dict[str, Any]) -> str:
        """문서 구조 정보를 간략한 텍스트로 요약"""
        if not structure_info:
            return "구조 정보 없음"

        try:
            summary_parts = []

            # 문서 기본 정보
            doc_info = structure_info.get("documentInfo", {})
            if doc_info:
                title = doc_info.get("title", "제목 없음")
                doc_type = doc_info.get("documentType", "미분류")
                summary_parts.append(f"문서: {title} ({doc_type})")

            # 구조 분석 요약
            structure_analysis = structure_info.get("structureAnalysis", [])
            if structure_analysis:
                section_count = len(structure_analysis)
                summary_parts.append(f"{section_count}개 주요 섹션")

            # 핵심 내용 요약
            core_content = structure_info.get("coreContent", {})
            if core_content:
                main_topic = core_content.get("mainTopic", "")
                if main_topic:
                    summary_parts.append(f"주제: {main_topic}")

            return " | ".join(summary_parts) if summary_parts else "구조 정보 없음"

        except Exception as e:
            self.logger.warning(f"구조 정보 요약 실패: {e}")
            return "구조 정보 처리 오류"

    def _call_llm_for_kg(self, prompt: str, llm_config: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 호출하여 Knowledge Graph 추출"""
        try:
            # LocalFileAnalyzer의 LLM 호출 메서드 활용
            # 임시 텍스트와 파일 정보로 호출
            result = self.analyzer.analyze_document_structure_with_llm(
                text=prompt,
                file_path="kg_extraction.txt",
                file_extension=".txt",
                overrides={
                    **llm_config,
                    "enabled": True
                }
            )

            if not result.get("success"):
                return {"success": False, "error": result.get("error", "LLM 호출 실패")}

            # LLM 응답 추출
            analysis = result.get("analysis", {})
            response_text = json.dumps(analysis) if isinstance(analysis, dict) else str(analysis)

            return {"success": True, "response": response_text}

        except Exception as e:
            self.logger.error(f"LLM 호출 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _parse_kg_response(self, response: str) -> Dict[str, Any]:
        """LLM 응답을 Knowledge Graph 구조로 파싱"""
        try:
            # JSON 응답 파싱 시도
            kg_data = json.loads(response)

            # 그래프 구조 검증
            if "graph" in kg_data:
                # Neo4j/Memgraph 스타일 (nodes, edges)
                return self._normalize_graph_structure(kg_data["graph"])
            elif "entities" in kg_data and "relationships" in kg_data:
                # 기존 스타일 (entities, relationships)
                return {
                    "nodes": kg_data.get("entities", []),
                    "edges": kg_data.get("relationships", [])
                }
            else:
                # 최상위 레벨이 직접 그래프인 경우
                return kg_data

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 파싱 실패: {e}")
            # 백업: 응답에서 JSON 블록 추출 시도
            return self._extract_json_from_text(response)
        except Exception as e:
            self.logger.error(f"KG 응답 파싱 오류: {e}", exc_info=True)
            return {"nodes": [], "edges": []}

    def _normalize_graph_structure(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """그래프 구조 정규화 (nodes, edges 형식으로 통일)"""
        return {
            "nodes": graph.get("nodes", graph.get("entities", [])),
            "edges": graph.get("edges", graph.get("relationships", []))
        }

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트에서 JSON 블록 추출"""
        import re

        # JSON 코드 블록 패턴 (```json ... ```)
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 직접 { } 블록 찾기
        brace_pattern = r'\{.*\}'
        match = re.search(brace_pattern, text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        self.logger.warning("JSON 추출 실패, 빈 그래프 반환")
        return {"nodes": [], "edges": []}

    def _enrich_kg_with_metadata(
        self,
        kg_data: Dict[str, Any],
        file_path: str,
        domain: str,
        structure_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Knowledge Graph에 메타데이터 추가"""
        nodes = kg_data.get("nodes", [])
        edges = kg_data.get("edges", [])

        # 통계 계산
        entity_types = {}
        relationship_types = {}

        for node in nodes:
            node_type = node.get("type", "Unknown")
            entity_types[node_type] = entity_types.get(node_type, 0) + 1

        for edge in edges:
            edge_type = edge.get("type", "UNKNOWN")
            relationship_types[edge_type] = relationship_types.get(edge_type, 0) + 1

        # 결과 구조 생성
        result = {
            "success": True,
            "file_path": file_path,
            "domain": domain,
            "extraction_date": datetime.now().isoformat(),
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "stats": {
                "entity_count": len(nodes),
                "relationship_count": len(edges),
                "entity_types": entity_types,
                "relationship_types": relationship_types,
                "density": self._calculate_graph_density(len(nodes), len(edges))
            },
            "metadata": {
                "source_document": Path(file_path).name,
                "domain": domain,
                "has_structure_info": structure_info is not None,
                "version": "1.0"
            }
        }

        return result

    def _calculate_graph_density(self, node_count: int, edge_count: int) -> float:
        """그래프 밀도 계산 (0~1 범위)"""
        if node_count <= 1:
            return 0.0
        max_possible_edges = node_count * (node_count - 1)  # 방향 그래프 기준
        return round(edge_count / max_possible_edges, 4) if max_possible_edges > 0 else 0.0

    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """오류 결과 생성"""
        return {
            "success": False,
            "error": error_message,
            "graph": {
                "nodes": [],
                "edges": []
            },
            "stats": {
                "entity_count": 0,
                "relationship_count": 0,
                "entity_types": {},
                "relationship_types": {},
                "density": 0.0
            }
        }

    def save_knowledge_graph(
        self,
        kg_result: Dict[str, Any],
        output_dir: Path,
        format: str = "json"
    ) -> Dict[str, str]:
        """
        Knowledge Graph를 파일로 저장

        Args:
            kg_result: Knowledge Graph 결과
            output_dir: 출력 디렉토리
            format: 저장 형식 (json, cypher, graphml)

        Returns:
            저장된 파일 경로 딕셔너리
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        try:
            if format == "json" or format == "all":
                # JSON 형식 저장
                json_path = output_dir / "knowledge_graph.json"
                with json_path.open('w', encoding='utf-8') as f:
                    json.dump(kg_result, f, ensure_ascii=False, indent=2)
                saved_files["json"] = str(json_path)
                self.logger.info(f"📝 Knowledge Graph JSON 저장: {json_path}")

            if format == "cypher" or format == "all":
                # Cypher 쿼리 형식 저장
                cypher_path = output_dir / "knowledge_graph.cypher"
                cypher_content = self._generate_cypher_queries(kg_result)
                with cypher_path.open('w', encoding='utf-8') as f:
                    f.write(cypher_content)
                saved_files["cypher"] = str(cypher_path)
                self.logger.info(f"📝 Knowledge Graph Cypher 저장: {cypher_path}")

            if format == "graphml" or format == "all":
                # GraphML 형식 저장
                graphml_path = output_dir / "knowledge_graph.graphml"
                graphml_content = self._generate_graphml(kg_result)
                with graphml_path.open('w', encoding='utf-8') as f:
                    f.write(graphml_content)
                saved_files["graphml"] = str(graphml_path)
                self.logger.info(f"📝 Knowledge Graph GraphML 저장: {graphml_path}")

            return saved_files

        except Exception as e:
            self.logger.error(f"❌ Knowledge Graph 저장 실패: {e}", exc_info=True)
            return saved_files

    def _generate_cypher_queries(self, kg_result: Dict[str, Any]) -> str:
        """Cypher CREATE 쿼리 생성 (Neo4j/Memgraph 호환)"""
        queries = []
        queries.append("// Knowledge Graph Cypher Queries")
        queries.append(f"// Generated: {datetime.now().isoformat()}\n")

        # 노드 생성 쿼리
        queries.append("// Create Nodes")
        for node in kg_result.get("graph", {}).get("nodes", []):
            node_id = node.get("id", "")
            node_type = node.get("type", "Node")
            properties = node.get("properties", {})

            # 프로퍼티 문자열 생성
            props_str = ", ".join([
                f"{k}: {self._cypher_value(v)}"
                for k, v in properties.items()
            ])

            query = f"CREATE (n:{node_type} {{id: '{node_id}', {props_str}}});"
            queries.append(query)

        queries.append("\n// Create Relationships")
        for edge in kg_result.get("graph", {}).get("edges", []):
            source = edge.get("source", "")
            target = edge.get("target", "")
            edge_type = edge.get("type", "RELATED_TO")
            properties = edge.get("properties", {})

            # 프로퍼티 문자열 생성
            props_str = ", ".join([
                f"{k}: {self._cypher_value(v)}"
                for k, v in properties.items()
            ])

            query = (
                f"MATCH (a {{id: '{source}'}}), (b {{id: '{target}'}}) "
                f"CREATE (a)-[r:{edge_type} {{{props_str}}}]->(b);"
            )
            queries.append(query)

        return "\n".join(queries)

    def _cypher_value(self, value: Any) -> str:
        """Python 값을 Cypher 값 문자열로 변환"""
        if isinstance(value, str):
            # 문자열 이스케이프
            escaped = value.replace("'", "\\'").replace('"', '\\"')
            return f"'{escaped}'"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            items = [self._cypher_value(v) for v in value]
            return f"[{', '.join(items)}]"
        elif value is None:
            return "null"
        else:
            return f"'{str(value)}'"

    def _generate_graphml(self, kg_result: Dict[str, Any]) -> str:
        """GraphML XML 형식 생성"""
        lines = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        lines.append('  <graph id="KnowledgeGraph" edgedefault="directed">')

        # 노드 추가
        for node in kg_result.get("graph", {}).get("nodes", []):
            node_id = node.get("id", "")
            node_type = node.get("type", "Node")
            lines.append(f'    <node id="{node_id}">')
            lines.append(f'      <data key="type">{node_type}</data>')

            # 프로퍼티 추가
            for key, value in node.get("properties", {}).items():
                lines.append(f'      <data key="{key}">{self._xml_escape(str(value))}</data>')

            lines.append('    </node>')

        # 엣지 추가
        for idx, edge in enumerate(kg_result.get("graph", {}).get("edges", [])):
            edge_id = edge.get("id", f"e{idx}")
            source = edge.get("source", "")
            target = edge.get("target", "")
            edge_type = edge.get("type", "RELATED_TO")

            lines.append(f'    <edge id="{edge_id}" source="{source}" target="{target}">')
            lines.append(f'      <data key="type">{edge_type}</data>')

            # 프로퍼티 추가
            for key, value in edge.get("properties", {}).items():
                lines.append(f'      <data key="{key}">{self._xml_escape(str(value))}</data>')

            lines.append('    </edge>')

        lines.append('  </graph>')
        lines.append('</graphml>')

        return "\n".join(lines)

    def _xml_escape(self, text: str) -> str:
        """XML 특수 문자 이스케이프"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
