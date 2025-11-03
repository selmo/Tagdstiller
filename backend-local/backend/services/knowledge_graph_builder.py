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
            raw_response = llm_response.get("response", "")
            self.logger.debug(f"🔍 LLM 원시 응답 (처음 500자): {raw_response[:500]}")
            kg_data = self._parse_kg_response(raw_response)

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
            # LLM 설정 추출
            provider = llm_config.get("provider", "gemini")

            if provider == "gemini":
                return self._call_gemini_for_kg(prompt, llm_config)
            elif provider == "openai":
                return self._call_openai_for_kg(prompt, llm_config)
            elif provider == "ollama":
                return self._call_ollama_for_kg(prompt, llm_config)
            else:
                return {"success": False, "error": f"지원하지 않는 LLM 프로바이더: {provider}"}

        except Exception as e:
            self.logger.error(f"LLM 호출 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _call_gemini_for_kg(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Gemini API 호출 (자동 재시도 포함)"""
        import requests
        import time

        api_key = config.get("api_key")
        model = config.get("model", "models/gemini-2.0-flash")
        base_url = config.get("base_url", "https://generativelanguage.googleapis.com")
        timeout = config.get("timeout", 600)
        max_retries = config.get("max_retries", 3)

        if not api_key:
            return {"success": False, "error": "Gemini API 키가 없습니다"}

        # Gemini API 엔드포인트
        url = f"{base_url}/v1beta/{model}:generateContent?key={api_key}"

        # 요청 본문
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": config.get("temperature", 0.1),
                "maxOutputTokens": config.get("max_tokens", 8192),
            }
        }

        # 재시도 로직 (exponential backoff)
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) * 2  # 2, 4, 8초
                    self.logger.warning(f"⏳ Rate limit 대기 중... {wait_time}초 ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                self.logger.info(f"📡 Gemini API 호출 시작... (모델: {model}, 시도: {attempt + 1}/{max_retries})")

                response = requests.post(url, json=payload, timeout=timeout)
                response.raise_for_status()

                result = response.json()

                # 응답 텍스트 추출
                candidates = result.get("candidates", [])
                if not candidates:
                    return {"success": False, "error": "Gemini 응답이 비어있습니다"}

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                if not parts:
                    return {"success": False, "error": "Gemini 응답에 텍스트가 없습니다"}

                response_text = parts[0].get("text", "")

                self.logger.info(f"✅ Gemini 응답 수신 완료: {len(response_text):,}자")

                return {"success": True, "response": response_text}

            except requests.exceptions.Timeout:
                return {"success": False, "error": f"Gemini API 타임아웃 ({timeout}초)"}
            except requests.exceptions.HTTPError as e:
                # 429 Too Many Requests - 재시도
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    self.logger.warning(f"⚠️ Rate limit 초과 (429), 재시도 {attempt + 1}/{max_retries}")
                    continue
                # 다른 HTTP 에러 또는 마지막 재시도 - 실패
                return {"success": False, "error": f"Gemini API 오류: {str(e)}"}
            except requests.exceptions.RequestException as e:
                return {"success": False, "error": f"Gemini API 오류: {str(e)}"}
            except Exception as e:
                self.logger.error(f"Gemini 호출 오류: {e}", exc_info=True)
                return {"success": False, "error": str(e)}

        # 모든 재시도 실패
        return {"success": False, "error": f"Gemini API rate limit 초과 - {max_retries}회 재시도 모두 실패"}

    def _call_openai_for_kg(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI API 호출"""
        try:
            import requests

            api_key = config.get("api_key")
            model = config.get("model", "gpt-4")
            base_url = config.get("base_url", "https://api.openai.com/v1")
            timeout = config.get("timeout", 600)

            if not api_key:
                return {"success": False, "error": "OpenAI API 키가 없습니다"}

            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": config.get("temperature", 0.1),
                "max_tokens": config.get("max_tokens", 8192),
            }

            self.logger.info(f"📡 OpenAI API 호출 시작... (모델: {model})")

            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()

            result = response.json()
            response_text = result["choices"][0]["message"]["content"]

            self.logger.info(f"✅ OpenAI 응답 수신 완료: {len(response_text):,}자")

            return {"success": True, "response": response_text}

        except Exception as e:
            self.logger.error(f"OpenAI 호출 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _call_ollama_for_kg(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ollama API 호출"""
        try:
            import requests

            base_url = config.get("base_url", "http://localhost:11434")
            model = config.get("model", "llama3.2")
            timeout = config.get("timeout", 600)

            url = f"{base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config.get("temperature", 0.1),
                }
            }

            self.logger.info(f"📡 Ollama API 호출 시작... (모델: {model})")

            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()

            result = response.json()
            response_text = result.get("response", "")

            self.logger.info(f"✅ Ollama 응답 수신 완료: {len(response_text):,}자")

            return {"success": True, "response": response_text}

        except Exception as e:
            self.logger.error(f"Ollama 호출 오류: {e}", exc_info=True)
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
            # 마크다운 코드 블록으로 감싸진 경우 예상되는 상황이므로 DEBUG 레벨로 기록
            self.logger.debug(f"JSON 직접 파싱 실패 (코드 블록 추출 시도): {e}")
            # 백업: 응답에서 JSON 블록 추출 시도
            extracted = self._extract_json_from_text(response)
            # 추출된 데이터도 구조 정규화 필요
            if "graph" in extracted:
                return self._normalize_graph_structure(extracted["graph"])
            elif "entities" in extracted and "relationships" in extracted:
                return {
                    "nodes": extracted.get("entities", []),
                    "edges": extracted.get("relationships", [])
                }
            else:
                return extracted
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
        """텍스트에서 JSON 블록 추출 (불완전한 JSON 복구 포함)"""
        import re

        # JSON 코드 블록 패턴 (```json ... ```) - greedy 매칭으로 전체 JSON 추출
        json_block_pattern = r'```(?:json)?\s*(\{.*\})\s*```'
        match = re.search(json_block_pattern, text, re.DOTALL)

        json_str = None
        if match:
            json_str = match.group(1)
            self.logger.info(f"✅ 마크다운 코드 블록에서 JSON 추출 ({len(json_str)}자)")
        else:
            # 직접 { } 블록 찾기 (greedy 매칭)
            brace_pattern = r'\{.*\}'
            match = re.search(brace_pattern, text, re.DOTALL)
            if match:
                json_str = match.group(0)
                self.logger.info(f"✅ 중괄호 블록에서 JSON 추출 ({len(json_str)}자)")

        if json_str:
            # 먼저 정상 파싱 시도
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                self.logger.warning(f"⚠️ JSON 파싱 실패, 불완전한 JSON 복구 시도: {e}")
                # 불완전한 JSON 복구 시도
                repaired = self._repair_incomplete_json(json_str)
                if repaired:
                    try:
                        result = json.loads(repaired)
                        self.logger.info(f"✅ 불완전한 JSON 복구 성공: {len(result.get('entities', []))}개 엔티티")
                        return result
                    except json.JSONDecodeError as e2:
                        self.logger.error(f"❌ JSON 복구 실패: {e2}")

        self.logger.warning("JSON 추출 실패, 빈 그래프 반환")
        return {"nodes": [], "edges": []}

    def _repair_incomplete_json(self, json_str: str) -> Optional[str]:
        """불완전한 JSON을 수정 (LLM 응답이 잘렸을 때)"""
        try:
            # 잘린 JSON의 일반적인 패턴 수정
            # 1. 마지막 객체가 불완전한 경우 제거
            # 2. 배열과 객체 닫기

            # 마지막 쉼표 뒤에 불완전한 항목이 있는지 확인
            last_comma_pos = json_str.rfind(',')
            if last_comma_pos > 0:
                # 마지막 쉼표 이후 내용 확인
                after_comma = json_str[last_comma_pos+1:].strip()
                # 완전한 객체인지 확인 (닫는 중괄호가 있는지)
                if after_comma and not after_comma.endswith('}'):
                    # 불완전한 객체 제거
                    json_str = json_str[:last_comma_pos]
                    self.logger.info(f"🔧 불완전한 마지막 객체 제거")

            # 필요한 닫는 괄호 추가
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')

            if open_brackets > 0:
                json_str += '\n  ]' * open_brackets
                self.logger.info(f"🔧 닫는 배열 괄호 {open_brackets}개 추가")

            if open_braces > 0:
                json_str += '\n}' * open_braces
                self.logger.info(f"🔧 닫는 객체 괄호 {open_braces}개 추가")

            return json_str
        except Exception as e:
            self.logger.error(f"JSON 복구 중 오류: {e}")
            return None

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

    # ========== 청킹 기반 Full KG 추출 (신규) ==========

    def build_full_knowledge_graph_with_chunking(
        self,
        text: str,
        file_path: str,
        domain: str = "general",
        structure_info: Optional[Dict[str, Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        max_chunk_tokens: int = 8000,
        output_dir: Optional[Path] = None,
        extraction_level: str = "standard"
    ) -> Dict[str, Any]:
        """
        구조 기반 청킹을 사용한 완전한 Knowledge Graph 생성

        Args:
            text: 문서 전체 텍스트
            extraction_level: 추출 수준 ("brief", "standard", "deep")
            file_path: 파일 경로
            domain: 문서 도메인
            structure_info: 문서 구조 정보
            llm_config: LLM 설정
            max_chunk_tokens: 청크당 최대 토큰 수

        Returns:
            병합된 완전한 Knowledge Graph
        """
        try:
            # 파일명에서 문서 제목 추출
            document_title = Path(file_path).stem  # 확장자 제외한 파일명
            self.logger.info(f"🔍 청킹 기반 Full KG 생성 시작: {document_title}")

            # 1. 문서 청킹
            from .document_chunker import StructuralChunker
            chunker = StructuralChunker()

            # 문서 구조 분석 및 청킹
            document_tree = chunker.analyzer.analyze_structure(text)
            chunker_level = chunker.determine_chunking_level(len(text), document_tree)
            chunks = chunker.create_chunks(document_tree, chunk_level=chunker_level)

            self.logger.info(f"📄 문서를 {len(chunks)}개 청크로 분할 완료")

            # 2. 각 청크에서 KG 추출
            chunk_graphs = []

            # 청크 디버그 디렉토리 생성
            if output_dir:
                chunk_debug_dir = Path(output_dir) / "chunk_kg_debug"
                chunk_debug_dir.mkdir(parents=True, exist_ok=True)
            else:
                chunk_debug_dir = None

            for idx, chunk_group in enumerate(chunks):
                chunk_id = f"chunk_{idx+1:03d}"
                chunk_text = chunk_group.get_total_content()
                parent_context = chunk_group.parent_context or "문서 루트"

                self.logger.info(f"🔍 청크 {idx+1}/{len(chunks)} KG 추출 중... ({len(chunk_text):,}자)")

                # 2-Phase 추출 사용 (엔티티 먼저, 관계 나중)
                kg_data = self._extract_kg_from_chunk_2phase(
                    chunk_text=chunk_text,
                    chunk_id=chunk_id,
                    parent_context=parent_context,
                    structure_info=structure_info,
                    llm_config=llm_config or {},
                    debug_dir=chunk_debug_dir,
                    extraction_level=extraction_level,
                    document_title=document_title
                )

                # kg_data가 None이면 이미 예외가 발생했을 것이므로 여기까지 오지 않음
                chunk_graphs.append({
                    "chunk_id": chunk_id,
                    "graph": kg_data,
                    "level": chunk_group.level,
                    "nodes_in_chunk": chunk_group.nodes
                })

            # 3. 청크별 KG 병합
            self.logger.info(f"🔗 {len(chunk_graphs)}개 청크 KG 병합 중...")
            merged_kg = self._merge_chunk_graphs(chunk_graphs)

            # 4. 메타데이터 추가
            result = self._enrich_kg_with_metadata(
                merged_kg,
                file_path,
                domain,
                structure_info
            )

            # 청킹 정보 추가
            result["chunking_stats"] = {
                "total_chunks": len(chunks),
                "successful_extractions": len(chunk_graphs),
                "max_chunk_tokens": max_chunk_tokens
            }

            self.logger.info(
                f"✅ Full KG 생성 완료: "
                f"{result['stats']['entity_count']}개 엔티티, "
                f"{result['stats']['relationship_count']}개 관계 "
                f"(from {len(chunks)} chunks)"
            )

            return result

        except Exception as e:
            self.logger.error(f"❌ Full KG 생성 실패: {e}", exc_info=True)
            return self._create_error_result(str(e))

    def _extract_kg_from_chunk_2phase(
        self,
        chunk_text: str,
        chunk_id: str,
        parent_context: str,
        structure_info: Optional[Dict[str, Any]],
        llm_config: Dict[str, Any],
        debug_dir: Optional[Path] = None,
        extraction_level: str = "standard",
        document_title: str = "Untitled Document"
    ) -> Optional[Dict[str, Any]]:
        """2-Phase 추출: 1단계 엔티티, 2단계 관계

        Args:
            extraction_level: 추출 수준 ("brief", "standard", "deep")
            document_title: 문서 제목 (파일명 또는 타이틀)
        """
        try:
            from prompts.templates import KnowledgeGraphPrompts
            import json

            # === Phase 1: 엔티티만 추출 ===
            # 추출 레벨에 따라 프롬프트 선택
            level_prompts = {
                "brief": KnowledgeGraphPrompts.PHASE1_ENTITY_BRIEF,
                "standard": KnowledgeGraphPrompts.PHASE1_ENTITY_STANDARD,
                "deep": KnowledgeGraphPrompts.PHASE1_ENTITY_DEEP
            }

            entity_template = level_prompts.get(extraction_level.lower(), level_prompts["standard"])

            self.logger.info(f"🔍 {chunk_id} Phase 1: 엔티티 추출 중... (레벨: {extraction_level}, 문서: {document_title})")

            entity_prompt = entity_template.format(text=chunk_text, document_title=document_title)

            # 디버그: Phase 1 프롬프트 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase1_prompt.txt").write_text(entity_prompt, encoding='utf-8')

            # Phase 1 LLM 호출
            phase1_response = self._call_llm_for_kg(entity_prompt, llm_config)

            if not phase1_response.get("success"):
                error_msg = f"{chunk_id} Phase 1 LLM 호출 실패: {phase1_response.get('error')}"
                self.logger.error(f"❌ {error_msg}")
                if debug_dir:
                    (debug_dir / f"{chunk_id}_phase1_error.txt").write_text(phase1_response.get('error', ''), encoding='utf-8')
                raise ValueError(error_msg)

            phase1_raw = phase1_response.get("response", "")

            # 디버그: Phase 1 응답 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase1_response.txt").write_text(phase1_raw, encoding='utf-8')

            # Phase 1 파싱
            entities_data = self._parse_kg_response(phase1_raw)
            entities = entities_data.get('entities', entities_data.get('nodes', []))

            if not entities:
                error_msg = f"{chunk_id} Phase 1 실패: 엔티티가 추출되지 않았습니다"
                self.logger.error(f"❌ {error_msg}")
                if debug_dir:
                    (debug_dir / f"{chunk_id}_phase1_parse_error.txt").write_text(
                        f"{error_msg}\n\nResponse: {phase1_raw[:1000]}", encoding='utf-8'
                    )
                raise ValueError(error_msg)

            self.logger.info(f"✅ {chunk_id} Phase 1 완료: {len(entities)}개 엔티티 추출")

            # === Phase 2: 관계만 추출 ===
            self.logger.info(f"🔗 {chunk_id} Phase 2: 관계 추출 중...")

            # 엔티티 목록을 JSON으로 변환 (간결하게)
            entities_json = json.dumps([
                {"id": e.get("id"), "type": e.get("type"), "name": e.get("properties", {}).get("name", "Unknown")}
                for e in entities
            ], ensure_ascii=False, indent=2)

            relation_prompt = KnowledgeGraphPrompts.PHASE2_RELATION_ONLY.format(
                entities_json=entities_json,
                text=chunk_text[:5000]  # 텍스트는 앞부분만 (토큰 절약)
            )

            # 디버그: Phase 2 프롬프트 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase2_prompt.txt").write_text(relation_prompt, encoding='utf-8')

            # Phase 2 LLM 호출
            phase2_response = self._call_llm_for_kg(relation_prompt, llm_config)

            if not phase2_response.get("success"):
                error_msg = f"{chunk_id} Phase 2 LLM 호출 실패: {phase2_response.get('error')}"
                self.logger.error(f"❌ {error_msg}")
                if debug_dir:
                    (debug_dir / f"{chunk_id}_phase2_error.txt").write_text(phase2_response.get('error', ''), encoding='utf-8')
                raise ValueError(error_msg)

            phase2_raw = phase2_response.get("response", "")

            # 디버그: Phase 2 응답 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase2_response.txt").write_text(phase2_raw, encoding='utf-8')

            # Phase 2 파싱
            relations_data = self._parse_kg_response(phase2_raw)
            relationships = relations_data.get('relationships', relations_data.get('edges', []))

            self.logger.info(f"✅ {chunk_id} Phase 2 완료: {len(relationships)}개 관계 추출")

            # === 결과 병합 ===
            kg_data = {
                "nodes": entities,
                "edges": relationships
            }

            # 디버그: 최종 KG 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_kg_2phase.json").write_text(
                    json.dumps(kg_data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )

            self.logger.info(
                f"✅ {chunk_id} 2-Phase 추출 완료: "
                f"{len(entities)}개 엔티티, {len(relationships)}개 관계"
            )

            return kg_data

        except Exception as e:
            self.logger.error(f"❌ {chunk_id} 2-Phase KG 추출 실패: {e}", exc_info=True)
            if debug_dir:
                (debug_dir / f"{chunk_id}_2phase_exception.txt").write_text(str(e), encoding='utf-8')
            raise

    def _extract_kg_from_chunk(
        self,
        chunk_text: str,
        chunk_id: str,
        parent_context: str,
        structure_info: Optional[Dict[str, Any]],
        llm_config: Dict[str, Any],
        debug_dir: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """단일 청크에서 KG 추출"""
        try:
            from prompts.templates import KnowledgeGraphPrompts

            # 구조 정보 요약
            structure_summary = self._summarize_structure(structure_info) if structure_info else "구조 정보 없음"

            # 상세 추출 프롬프트 생성
            prompt = KnowledgeGraphPrompts.DETAILED_KG_EXTRACTION.format(
                text=chunk_text,
                chunk_id=chunk_id,
                structure_info=structure_summary,
                parent_context=parent_context
            )

            # 디버그: 청크 텍스트 저장
            if debug_dir:
                chunk_text_file = debug_dir / f"{chunk_id}_text.txt"
                chunk_text_file.write_text(chunk_text, encoding='utf-8')

            # 디버그: 프롬프트 저장
            if debug_dir:
                prompt_file = debug_dir / f"{chunk_id}_prompt.txt"
                prompt_file.write_text(prompt, encoding='utf-8')
                self.logger.debug(f"📝 {chunk_id} 프롬프트 저장: {prompt_file}")

            # LLM 호출
            llm_response = self._call_llm_for_kg(prompt, llm_config)

            if not llm_response.get("success"):
                error_msg = f"{chunk_id} LLM 호출 실패: {llm_response.get('error')}"
                self.logger.error(f"❌ {error_msg}")
                # 디버그: 오류 저장
                if debug_dir:
                    error_file = debug_dir / f"{chunk_id}_error.txt"
                    error_file.write_text(llm_response.get('error', 'Unknown error'), encoding='utf-8')
                # 치명적 오류로 예외 발생시켜 전체 프로세스 중단
                raise ValueError(error_msg)

            # 응답 파싱
            raw_response = llm_response.get("response", "")

            # 디버그: LLM 응답 저장
            if debug_dir:
                response_file = debug_dir / f"{chunk_id}_response.txt"
                response_file.write_text(raw_response, encoding='utf-8')
                self.logger.debug(f"📝 {chunk_id} 응답 저장: {response_file}")

            kg_data = self._parse_kg_response(raw_response)

            # 핵심 검증: 파싱 결과가 비어있으면 치명적 오류로 처리
            if not kg_data.get('nodes') and not kg_data.get('edges'):
                error_msg = f"{chunk_id} KG 추출 실패: LLM 응답 파싱 결과가 비어있습니다. JSON 형식 오류 또는 max_tokens 초과 가능성"
                self.logger.error(f"❌ {error_msg}")

                # 디버그: 파싱 실패 상세 정보 저장
                if debug_dir:
                    error_detail_file = debug_dir / f"{chunk_id}_parse_error.txt"
                    error_detail_file.write_text(
                        f"Error: {error_msg}\n\n"
                        f"Response length: {len(raw_response)}\n"
                        f"Response preview (last 500 chars):\n{raw_response[-500:]}\n\n"
                        f"Parsed result: {json.dumps(kg_data, ensure_ascii=False, indent=2)}",
                        encoding='utf-8'
                    )

                # 치명적 오류로 None 반환하여 전체 프로세스 중단
                raise ValueError(error_msg)

            # 디버그: 파싱된 KG 데이터 저장
            if debug_dir:
                kg_file = debug_dir / f"{chunk_id}_kg.json"
                kg_file.write_text(
                    json.dumps(kg_data, ensure_ascii=False, indent=2),
                    encoding='utf-8'
                )
                self.logger.debug(f"📝 {chunk_id} KG 저장: {kg_file}")

            self.logger.info(
                f"✅ {chunk_id} 추출 완료: "
                f"{len(kg_data.get('nodes', []))}개 엔티티, "
                f"{len(kg_data.get('edges', []))}개 관계"
            )

            return kg_data

        except Exception as e:
            self.logger.error(f"❌ {chunk_id} KG 추출 실패: {e}", exc_info=True)
            # 디버그: 예외 저장
            if debug_dir:
                exception_file = debug_dir / f"{chunk_id}_exception.txt"
                exception_file.write_text(str(e), encoding='utf-8')
            # 치명적 오류이므로 예외를 다시 발생시켜 전체 프로세스 중단
            raise

    def _merge_chunk_graphs(self, chunk_graphs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """여러 청크의 KG를 하나로 병합"""
        merged_nodes = []
        merged_edges = []
        node_id_map = {}  # 중복 제거를 위한 매핑

        for chunk_data in chunk_graphs:
            chunk_id = chunk_data["chunk_id"]
            graph = chunk_data["graph"]

            # 노드 병합 (ID 충돌 방지)
            for node in graph.get("nodes", []):
                original_id = node["id"]
                new_id = f"{chunk_id}_{original_id}"

                # 동일한 엔티티 중복 체크 (이름과 타입이 같으면 병합)
                node_key = (node.get("type"), node.get("properties", {}).get("name"))

                if node_key in node_id_map:
                    # 기존 노드 ID 사용 (중복 제거)
                    node_id_map[original_id] = node_id_map[node_key]
                else:
                    # 새 노드 추가
                    node["id"] = new_id
                    merged_nodes.append(node)
                    node_id_map[original_id] = new_id
                    node_id_map[node_key] = new_id

            # 관계 병합 (ID 업데이트)
            for edge in graph.get("edges", []):
                # 원본 ID를 병합된 ID로 변환
                source = edge.get("source", "")
                target = edge.get("target", "")

                # chunk_id 접두사 제거 후 매핑
                source_base = source.split("_", 1)[-1] if "_" in source else source
                target_base = target.split("_", 1)[-1] if "_" in target else target

                new_source = node_id_map.get(source_base, f"{chunk_id}_{source}")
                new_target = node_id_map.get(target_base, f"{chunk_id}_{target}")

                edge["source"] = new_source
                edge["target"] = new_target
                edge["id"] = f"{chunk_id}_{edge.get('id', len(merged_edges))}"

                merged_edges.append(edge)

        self.logger.info(
            f"🔗 병합 완료: {len(merged_nodes)}개 엔티티 (중복 제거 후), "
            f"{len(merged_edges)}개 관계"
        )

        return {
            "nodes": merged_nodes,
            "edges": merged_edges
        }
