"""
Knowledge Graph Builder Service

문서 전체를 Knowledge Graph로 변환하는 전용 서비스
LLM을 사용하여 엔티티와 관계를 추출하고 그래프 구조로 변환합니다.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
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
        max_retries = config.get("max_retries", 5)  # 3 → 5로 증가
        base_delay = config.get("base_delay", 15)  # 기본 15초: 모든 요청 전 대기

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

        # 재시도 로직 (exponential backoff with longer waits + base delay)
        for attempt in range(max_retries):
            try:
                # 모든 요청 전 기본 대기 (rate limit 회피)
                if attempt == 0 and base_delay > 0:
                    self.logger.info(f"⏳ Rate limit 회피 대기... {base_delay}초")
                    time.sleep(base_delay)
                elif attempt > 0:
                    # 재시도 시 exponential backoff
                    wait_time = (2 ** attempt) * 5  # 5, 10, 20, 40, 80초
                    self.logger.warning(f"⏳ Rate limit 대기 중... {wait_time}초 ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)

                api_call_start = time.time()
                self.logger.info(f"📡 Gemini API 호출 시작... (모델: {model}, 시도: {attempt + 1}/{max_retries})")

                response = requests.post(url, json=payload, timeout=timeout)
                response.raise_for_status()

                result = response.json()
                api_call_duration = time.time() - api_call_start

                # 응답 텍스트 추출
                candidates = result.get("candidates", [])
                if not candidates:
                    return {"success": False, "error": "Gemini 응답이 비어있습니다"}

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                if not parts:
                    return {"success": False, "error": "Gemini 응답에 텍스트가 없습니다"}

                response_text = parts[0].get("text", "")

                # 토큰 사용량 추출 (Gemini API는 usageMetadata에 토큰 정보 포함)
                usage_metadata = result.get("usageMetadata", {})
                input_tokens = usage_metadata.get("promptTokenCount", 0)
                output_tokens = usage_metadata.get("candidatesTokenCount", 0)
                total_tokens = usage_metadata.get("totalTokenCount", 0)

                self.logger.info(
                    f"✅ Gemini 응답 수신 완료: {len(response_text):,}자 "
                    f"(소요시간: {api_call_duration:.2f}초, "
                    f"토큰: 입력 {input_tokens:,} + 출력 {output_tokens:,} = 총 {total_tokens:,})"
                )

                return {
                    "success": True,
                    "response": response_text,
                    "duration": api_call_duration,
                    "tokens": {
                        "input": input_tokens,
                        "output": output_tokens,
                        "total": total_tokens
                    }
                }

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
        """OpenAI API 호출 (새로운 /v1/responses API 사용)"""
        try:
            import requests

            api_key = config.get("api_key")
            model = config.get("model", "gpt-4")
            base_url = config.get("base_url", "https://api.openai.com/v1")
            timeout = config.get("timeout", 600)

            if not api_key:
                return {"success": False, "error": "OpenAI API 키가 없습니다"}

            # GPT-5 모델은 새로운 /v1/responses 엔드포인트 사용
            use_responses_api = "gpt-5" in model.lower()

            if use_responses_api:
                url = f"{base_url}/responses"
            else:
                url = f"{base_url}/chat/completions"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            # GPT-5 모델의 경우 새로운 API 형식 사용
            if use_responses_api:
                payload = {
                    "model": model,
                    "input": prompt,
                    "reasoning": {
                        "effort": config.get("reasoning_effort", "minimal")  # minimal, medium, high
                    }
                }
                self.logger.info(f"📡 OpenAI /v1/responses API 호출 (모델: {model}, reasoning: {payload['reasoning']['effort']})")
            else:
                # 기존 chat/completions API 형식
                max_output = config.get("max_tokens", config.get("max_completion_tokens", 8192))

                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": config.get("temperature", 0.1),
                }

                # 모델에 따라 적절한 파라미터 사용
                if "o1" in model.lower() or "gpt-4o" in model.lower():
                    payload["max_completion_tokens"] = max_output
                else:
                    payload["max_tokens"] = max_output

                self.logger.info(f"📡 OpenAI /v1/chat/completions API 호출 (모델: {model})")

            api_call_start = time.time()
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)

            # 400 오류 시 상세 에러 메시지 로깅
            if response.status_code == 400:
                try:
                    error_detail = response.json()
                    self.logger.error(f"❌ OpenAI 400 Bad Request 상세:")
                    self.logger.error(f"   - 오류 메시지: {error_detail.get('error', {}).get('message', 'Unknown')}")
                    self.logger.error(f"   - 요청 모델: {model}")
                    self.logger.error(f"   - API 엔드포인트: {url}")
                    self.logger.error(f"   - 프롬프트 길이: {len(prompt)} 문자")
                except:
                    pass

            response.raise_for_status()

            result = response.json()

            # 응답 파싱 (API 형식에 따라 다름)
            if use_responses_api:
                # GPT-5 API 응답 구조: {"output": [reasoning, message], ...}
                if isinstance(result, dict) and "output" in result:
                    output_array = result["output"]

                    # output 배열에서 'message' 타입 찾기
                    message_obj = None
                    for item in output_array:
                        if item.get('type') == 'message':
                            message_obj = item
                            break

                    if message_obj and 'content' in message_obj:
                        content_list = message_obj['content']
                        for content_item in content_list:
                            if content_item.get('type') == 'output_text':
                                response_text = content_item.get('text', '')
                                self.logger.info(f"✅ /v1/responses API 응답 파싱 성공: {len(response_text)}자")
                                break
                        else:
                            # output_text를 찾지 못함
                            self.logger.error(f"❌ /v1/responses API: output_text를 찾지 못함")
                            raise RuntimeError("OpenAI /v1/responses API: output_text를 찾을 수 없음")
                    else:
                        self.logger.error(f"❌ /v1/responses API: message 객체를 찾지 못함")
                        raise RuntimeError("OpenAI /v1/responses API: message 객체를 찾을 수 없음")
                else:
                    self.logger.error(f"❌ 예상하지 못한 응답 형식")
                    raise RuntimeError(f"OpenAI /v1/responses API 응답 형식 오류")
            else:
                # 기존 chat/completions API
                response_text = result["choices"][0]["message"]["content"]

            # 토큰 사용량 추출 (OpenAI API는 usage 필드에 토큰 정보 포함)
            usage = result.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # 응답 시간 계산
            api_call_duration = time.time() - api_call_start if 'api_call_start' in locals() else 0

            self.logger.info(
                f"✅ OpenAI 응답 수신 완료: {len(response_text):,}자 "
                f"(토큰: 입력 {input_tokens:,} + 출력 {output_tokens:,} = 총 {total_tokens:,})"
            )

            return {
                "success": True,
                "response": response_text,
                "duration": api_call_duration,
                "tokens": {
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                }
            }

        except requests.exceptions.HTTPError as e:
            # HTTP 오류 상세 로깅
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"{e} | Detail: {error_detail.get('error', {}).get('message', error_detail)}"
                except:
                    pass
            self.logger.error(f"OpenAI HTTP 오류: {error_msg}", exc_info=True)
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.logger.error(f"OpenAI 호출 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _call_ollama_for_kg(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Ollama API 호출"""
        try:
            import requests

            # config 중첩 구조 처리: {"provider": "ollama", "config": {...}}
            ollama_config = config.get("config", config)  # config 안의 config를 사용, 없으면 전체 사용

            base_url = ollama_config.get("base_url", "http://localhost:11434")
            model = ollama_config.get("model", "llama3.2")
            timeout = ollama_config.get("timeout", 600)

            url = f"{base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": ollama_config.get("temperature", 0.1),
                }
            }

            self.logger.info(f"📡 Ollama API 호출 시작... (모델: {model}, URL: {base_url})")

            # Retry logic for server errors (500, 502, 503, 504)
            max_retries = 3
            retry_delays = [3, 6, 12]  # seconds

            for attempt in range(max_retries):
                try:
                    response = requests.post(url, json=payload, timeout=timeout)
                    response.raise_for_status()

                    result = response.json()
                    response_text = result.get("response", "")

                    self.logger.info(f"✅ Ollama 응답 수신 완료: {len(response_text):,}자")

                    return {"success": True, "response": response_text}

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code in [500, 502, 503, 504]:
                        if attempt < max_retries - 1:
                            delay = retry_delays[attempt]
                            self.logger.warning(
                                f"⚠️ Ollama 서버 오류 {e.response.status_code}, "
                                f"{delay}초 후 재시도 ({attempt + 1}/{max_retries})"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            self.logger.error(f"❌ Ollama 서버 오류 (최대 재시도 횟수 도달): {e}")
                            return {"success": False, "error": str(e)}
                    else:
                        # Other HTTP errors (4xx) - don't retry
                        self.logger.error(f"Ollama HTTP 오류: {e}", exc_info=True)
                        return {"success": False, "error": str(e)}
                except Exception as e:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        self.logger.warning(
                            f"⚠️ Ollama 호출 오류, {delay}초 후 재시도 ({attempt + 1}/{max_retries}): {e}"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise

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

                        # 디버그: 실패한 JSON을 파일로 저장
                        try:
                            debug_dir = Path("/tmp/kg_json_debug")
                            debug_dir.mkdir(exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                            original_file = debug_dir / f"original_{timestamp}.txt"
                            repaired_file = debug_dir / f"repaired_{timestamp}.txt"
                            error_file = debug_dir / f"error_{timestamp}.txt"

                            with open(original_file, 'w', encoding='utf-8') as f:
                                f.write(json_str)
                            with open(repaired_file, 'w', encoding='utf-8') as f:
                                f.write(repaired)
                            with open(error_file, 'w', encoding='utf-8') as f:
                                f.write(f"Original error: {e}\n")
                                f.write(f"Repair error: {e2}\n")
                                f.write(f"Error position: line {e2.lineno if hasattr(e2, 'lineno') else '?'}, col {e2.colno if hasattr(e2, 'colno') else '?'}\n")

                            self.logger.warning(f"🐛 JSON 디버그 파일 저장: {debug_dir}")
                        except Exception as save_error:
                            self.logger.debug(f"디버그 파일 저장 실패: {save_error}")

                        # 로그에도 샘플 출력
                        self.logger.debug(f"원본 JSON (처음 500자): {json_str[:500]}")
                        self.logger.debug(f"원본 JSON (마지막 500자): {json_str[-500:]}")

        self.logger.warning("JSON 추출 실패, 빈 그래프 반환")
        return {"nodes": [], "edges": []}

    def _repair_incomplete_json(self, json_str: str) -> Optional[str]:
        """불완전한 JSON을 수정 (LLM 응답이 잘렸을 때)"""
        try:
            import re

            # 0-0. JSON 주석 제거 (LLM이 잘못 생성한 주석)
            # 패턴 1: // 주석 (한 줄 주석)
            # 패턴 2: /* */ 주석 (블록 주석)
            before_comment = json_str.count('//')
            # 문자열 외부의 // 주석만 제거 (문자열 내부 // 는 유지)
            json_str = re.sub(r',\s*//[^\n]*', ',', json_str)  # ", // comment" → ","
            json_str = re.sub(r'\}\s*,\s*//[^\n]*', '},', json_str)  # "}, // comment" → "},"
            json_str = re.sub(r'//[^\n]*\n', '\n', json_str)  # 독립 주석 라인 제거
            after_comment = json_str.count('//')
            if before_comment > after_comment:
                self.logger.info(f"🔧 JSON 주석 제거 완료 ({before_comment - after_comment}개)")

            # 블록 주석 제거
            before_block = json_str.count('/*')
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            after_block = json_str.count('/*')
            if before_block > after_block:
                self.logger.info(f"🔧 JSON 블록 주석 제거 완료 ({before_block - after_block}개)")

            # 0-0-1. 배열이 너무 일찍 닫힌 경우 수정
            # 패턴 1: ...}]}\n{"id": ... → ...}},\n{"id": ... (entities 배열 조기 종료)
            # 패턴 2: ...}}],\n{"id": ... → ...}},\n{"id": ... (중간 배열 닫힘)
            early_close_pattern1 = r'(\}\})\s*\]\s*\}\s*,?\s*\n(\s*\{\s*"id":)'
            matches1 = list(re.finditer(early_close_pattern1, json_str))
            if matches1:
                for match in reversed(matches1):
                    json_str = json_str[:match.start()] + match.group(1) + ',\n' + match.group(2) + json_str[match.end():]
                self.logger.info(f"🔧 배열 조기 종료 수정 (패턴1: ]}}): {len(matches1)}개")

            # 패턴 2: 중간에 배열이 닫힌 경우
            early_close_pattern2 = r'(\}\})\s*\]\s*,\s*\n(\s*\{\s*"id":)'
            matches2 = list(re.finditer(early_close_pattern2, json_str))
            if matches2:
                for match in reversed(matches2):
                    json_str = json_str[:match.start()] + match.group(1) + ',\n' + match.group(2) + json_str[match.end():]
                self.logger.info(f"🔧 배열 조기 종료 수정 (패턴2: ]],): {len(matches2)}개")

            # 패턴 3: 엔티티 뒤에 추가 닫는 중괄호와 줄바꿈
            # ...}}\n    },\n\n    {"id": ... → ...}},\n\n    {"id": ...
            # 이 패턴은 TableRow 같은 엔티티 뒤에 잘못된 중첩 닫기가 있을 때 발생
            extra_closing_pattern = r'(\}\})\s*\n\s+\}\s*,\s*\n+(\s*\{\s*"id":)'
            matches3 = list(re.finditer(extra_closing_pattern, json_str))
            if matches3:
                for match in reversed(matches3):
                    # 다음 엔티티의 들여쓰기 보존
                    next_indent = match.group(2)
                    json_str = json_str[:match.start()] + match.group(1) + ',\n' + next_indent + json_str[match.end():]
                self.logger.info(f"🔧 엔티티 뒤 추가 닫는 중괄호 제거 (패턴3): {len(matches3)}개")

            # 패턴 4: 문자열 값 내부의 잘못된 중괄호 (특히 notes 필드)
            # "notes": "Contextual} placeholder" → "notes": "Contextual placeholder"
            # 문자열 내부의 단독 } 또는 { 제거
            string_brace_pattern = r'("\w+"\s*:\s*"[^"]*?)(\}|\{)([^"]*")'
            before_str_fix = json_str.count('"}')

            def fix_string_braces(match):
                """문자열 값 내부의 단독 중괄호 제거"""
                prefix = match.group(1)  # "field": "text before
                brace = match.group(2)    # } or {
                suffix = match.group(3)   # text after"

                # 중괄호가 문자열 중간에 있으면 제거
                # 단, JSON 구조가 아닌 일반 텍스트로 판단되는 경우만
                if brace in '{}' and not suffix.startswith('}}'):  # 실제 JSON 종료가 아닌 경우
                    return prefix + suffix  # 중괄호 제거
                return match.group(0)  # 변경 없음

            json_str = re.sub(string_brace_pattern, fix_string_braces, json_str)
            after_str_fix = json_str.count('"}')
            if before_str_fix != after_str_fix:
                self.logger.info(f"🔧 문자열 값 내부 잘못된 중괄호 제거 (패턴4): {abs(before_str_fix - after_str_fix)}개")

            # 0. 여분의 닫는 중괄호 제거 (특히 }}}+ 패턴)
            # 패턴 1: properties 내부 여분 괄호 - "name": "value"}}} → "name": "value"}}
            # 패턴 2: 배열 항목 여분 괄호 - {...}}}}, → {...}},

            # 특정 패턴 수정: properties 끝에 여분 중괄호
            # "name": "value"}}}, → "name": "value"}},
            before_fix = json_str.count('}}}')
            json_str = re.sub(r'("\s*:\s*"[^"]*")\}\}\}', r'\1}}', json_str)
            after_fix = json_str.count('}}}')
            if before_fix > after_fix:
                self.logger.info(f"🔧 properties 값 뒤 여분 중괄호 제거 ({before_fix - after_fix}개)")

            # 여전히 }}} 패턴이 남아있으면 일괄 수정
            remaining_triple = json_str.count('}}}')
            if remaining_triple > 0:
                json_str = re.sub(r'\}\}\}', '}}', json_str)
                self.logger.info(f"🔧 남은 3개 연속 닫는 중괄호 수정 완료 ({remaining_triple}개)")

            # 배열 아이템 뒤 여분 괄호: }}}, → }},
            json_str = re.sub(r'\}\}\},', '}},', json_str)

            # 이중 닫는 괄호 패턴 정리
            double_closing_pattern = r'(\{[^}]*\})\s*\}\s*\}'
            before_count = json_str.count('}}')
            json_str = re.sub(r'(\})\s+\}\s*\}', r'\1}', json_str)
            after_count = json_str.count('}}')
            if before_count != after_count:
                self.logger.info(f"🔧 이중 닫는 괄호 수정 완료 ({before_count - after_count}개)")

            # 0-1. 잘못된 엔티티 형식 수정
            # {"id": "n156", "type": "LegalRegulation", "name": "..."}
            # → {"id": "n156", "type": "LegalRegulation", "properties": {"name": "..."}}
            malformed_entity_pattern = r'\{"id":\s*"([^"]+)",\s*"type":\s*"([^"]+)",\s*("name"|"text"|"value"):\s*"([^"]*)"(\s*,\s*"[^"]+"\s*:\s*"[^"]*")*\s*\}'

            def fix_malformed_entity(match):
                entity_id = match.group(1)
                entity_type = match.group(2)
                field_name = match.group(3).strip('"')  # "name" → name
                field_value = match.group(4)

                # 추가 필드가 있는지 확인
                extra_fields = match.group(5) or ""

                # properties 형식으로 변환
                properties_content = f'"{field_name}": "{field_value}"'

                # 추가 필드가 있으면 properties 안에 포함
                if extra_fields:
                    # 쉼표로 시작하는 추가 필드를 properties 안에 넣기
                    properties_content += extra_fields

                result = f'{{"id": "{entity_id}", "type": "{entity_type}", "properties": {{{properties_content}}}}}'
                return result

            fixed_entities_count = 0
            matches = list(re.finditer(malformed_entity_pattern, json_str))
            for match in reversed(matches):  # 뒤에서부터 수정하여 인덱스 유지
                fixed = fix_malformed_entity(match)
                json_str = json_str[:match.start()] + fixed + json_str[match.end():]
                fixed_entities_count += 1

            if fixed_entities_count > 0:
                self.logger.info(f"🔧 잘못된 엔티티 형식 {fixed_entities_count}개 수정 완료 (properties 추가)")

            # 0-2. properties 뒤에 추가 필드가 있는 경우 수정
            # {"properties": {...},"row_count": 17, "column_count": 3}
            # → {"properties": {..., "row_count": 17, "column_count": 3}}
            properties_with_external_fields = r'("properties"\s*:\s*\{[^}]+\})\s*,\s*("([^"]+)"\s*:\s*([^,}\s]+)(?:\s*,\s*"([^"]+)"\s*:\s*([^,}\s]+))*)'

            def fix_properties_external_fields(match):
                """properties 외부의 필드를 내부로 이동"""
                properties_part = match.group(1)  # "properties": {...}
                external_fields = match.group(2)  # "field": value, "field2": value2

                # properties 내용 추출 (마지막 } 제거)
                if properties_part.endswith('}'):
                    properties_content = properties_part[:-1]  # "properties": {...
                else:
                    return match.group(0)  # 변경 없음

                # 외부 필드를 properties 안으로 이동
                result = properties_content + ", " + external_fields + "}"
                return result

            json_str_before = json_str
            json_str = re.sub(properties_with_external_fields, fix_properties_external_fields, json_str)
            if json_str != json_str_before:
                self.logger.info(f"🔧 properties 외부 필드를 내부로 이동 완료")

            # 1. 제어 문자 이스케이프 처리 (JSON 파싱 오류 방지)
            def escape_control_chars(match):
                """JSON 문자열 내 제어 문자를 이스케이프"""
                s = match.group(0)
                # 제어 문자를 이스케이프된 형태로 변환
                s = s.replace('\n', '\\n')
                s = s.replace('\r', '\\r')
                s = s.replace('\t', '\\t')
                s = s.replace('\b', '\\b')
                s = s.replace('\f', '\\f')
                # 기타 제어 문자 (ASCII 0-31) 제거
                s = ''.join(char if ord(char) >= 32 or char in '\n\r\t\b\f' else '' for char in s)
                return s

            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', escape_control_chars, json_str)
            self.logger.info(f"🔧 제어 문자 이스케이프 처리 완료")

            # 2. 잘못된 백슬래시 이스케이프 처리
            def fix_escapes_in_strings(match):
                """문자열 내부의 잘못된 이스케이프 수정

                유효한 JSON 이스케이프: " \\ / b f n r t u
                잘못된 이스케이프 (예: \_ \() 는 백슬래시를 제거
                """
                s = match.group(0)
                # 잘못된 이스케이프: 백슬래시 뒤에 유효하지 않은 문자가 오는 경우
                # 해결: 백슬래시를 제거 (예: /\_ -> /_, /\( -> /()
                s = re.sub(r'\\(?!["\\/bfnrtu])', '', s)
                return s

            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_escapes_in_strings, json_str)
            self.logger.info(f"🔧 백슬래시 이스케이프 수정 완료 (잘못된 이스케이프 제거)")

            # 2. LLM이 생성한 잘못된 JSON 패턴 수정
            # 패턴: {"properties": {...}},\n    "name": "..."}}, → {"properties": {...}}},
            # 이는 LLM이 properties 닫은 후 외부에 중복 필드를 추가한 경우
            # 예: {"properties": {"name": "A"}}, "name": "A"}}
            malformed_pattern = r'("properties"\s*:\s*\{[^}]+\})\s*\}\s*,\s*("[^"]+"\s*:\s*"[^"]*")(\s*\}\s*\})'
            def fix_malformed_properties(match):
                properties_part = match.group(1)  # "properties": {...}
                external_field = match.group(2)   # "name": "값"
                closing = match.group(3)           # }}

                # 외부 필드 파싱
                field_match = re.match(r'"(\w+)"\s*:\s*"([^"]*)"', external_field)
                if field_match:
                    field_name = field_match.group(1)
                    field_value = field_match.group(2)

                    # 외부 필드가 이미 properties 안에 있는지 확인
                    if f'"{field_name}"' in properties_part:
                        # 중복이므로 외부 필드 제거하고 properties만 유지
                        self.logger.debug(f"🔧 중복 필드 '{field_name}' 제거 (properties 내부에 이미 존재)")
                        return properties_part + "}" + closing
                    else:
                        # properties 안에 없으면 추가
                        self.logger.debug(f"🔧 외부 필드 '{field_name}'를 properties 안으로 이동")
                        return properties_part[:-1] + f', "{field_name}": "{field_value}"' + "}}" + closing
                else:
                    # 파싱 실패 시 원본 유지
                    return match.group(0)

            json_str = re.sub(malformed_pattern, fix_malformed_properties, json_str, flags=re.DOTALL)
            fixed_count = len(re.findall(malformed_pattern, json_str, flags=re.DOTALL))
            if fixed_count > 0:
                self.logger.info(f"🔧 잘못된 JSON 패턴 {fixed_count}개 수정 완료 (중복 필드 처리)")

            # 3. 불완전한 JSON 객체/배열 찾아서 제거
            # 전략: 마지막 완전한 객체/배열까지만 유지

            # 2-1. 닫는 괄호가 부족한 경우 먼저 처리
            open_braces = json_str.count('{') - json_str.count('}')
            open_brackets = json_str.count('[') - json_str.count(']')

            # 2-2. 배열 내에서 불완전한 마지막 항목 제거
            # "entities": [ {...}, {...}, {불완전 <- 여기를 제거
            # 전략: 마지막 쉼표 이후가 완전한 객체가 아니면 마지막 쉼표부터 제거
            if '"entities"' in json_str or '"nodes"' in json_str:
                # 마지막 쉼표 위치 찾기 (문자열 내부 제외)
                last_comma = -1
                in_string = False
                escape_next = False

                for i, char in enumerate(json_str):
                    if escape_next:
                        escape_next = False
                        continue
                    if char == '\\':
                        escape_next = True
                        continue
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    if in_string:
                        continue

                    if char == ',':
                        # 배열 내부의 쉼표인지 확인 (depth 체크는 복잡하니 단순화)
                        last_comma = i

                # 마지막 쉼표 이후 첫 번째 객체가 완전한지 확인
                if last_comma > 0:
                    after_comma = json_str[last_comma+1:]

                    # 쉼표 이후 첫 번째 객체의 괄호 균형 확인
                    first_obj_brace_count = 0
                    in_string = False
                    escape_next = False
                    obj_started = False
                    obj_ended = False

                    for char in after_comma:
                        if escape_next:
                            escape_next = False
                            continue
                        if char == '\\':
                            escape_next = True
                            continue
                        if char == '"' and not escape_next:
                            in_string = not in_string
                            continue
                        if in_string:
                            continue

                        if char == '{':
                            first_obj_brace_count += 1
                            obj_started = True
                        elif char == '}':
                            first_obj_brace_count -= 1
                            if obj_started and first_obj_brace_count == 0:
                                obj_ended = True
                                break  # 첫 번째 객체 끝
                        elif char in ('[', ']') and not obj_started:
                            # 객체 시작 전에 배열 괄호 나옴 → 이미 배열 닫혔음
                            break

                    # 첫 번째 객체가 불완전하면 (시작했지만 안 닫힘)
                    if obj_started and not obj_ended:
                        json_str = json_str[:last_comma].strip()
                        self.logger.info(f"🔧 불완전한 마지막 항목 제거 (괄호 불균형: {first_obj_brace_count})")

                        # 적절한 닫기 추가
                        if not json_str.rstrip().endswith(']'):
                            json_str = json_str.rstrip() + '\n  ]\n}'
                            self.logger.debug(f"🔧 배열 및 객체 닫기 추가")

            # 3. Trailing comma 제거 (,] 또는 ,} 형태)
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)
            self.logger.debug(f"🔧 Trailing comma 제거 완료")

            # 4. 빈 값 처리 (: , 또는 : } 또는 : ] 형태)
            json_str = re.sub(r':\s*,', ': null,', json_str)
            json_str = re.sub(r':\s*}', ': null}', json_str)
            json_str = re.sub(r':\s*]', ': null]', json_str)
            self.logger.debug(f"🔧 빈 값을 null로 대체 완료")

            # 5. 필요한 닫는 괄호 재계산 및 추가
            # 먼저 현재 상태 파악 (문자열 내부 제외)
            brace_count = 0
            bracket_count = 0
            in_string = False
            escape_next = False

            for char in json_str:
                if escape_next:
                    escape_next = False
                    continue
                if char == '\\':
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue

                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                elif char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1

            # 필요한 닫는 괄호 추가
            if bracket_count > 0:
                json_str += '\n]' * bracket_count
                self.logger.info(f"🔧 닫는 배열 괄호 {bracket_count}개 추가")

            if brace_count > 0:
                json_str += '\n}' * brace_count
                self.logger.info(f"🔧 닫는 객체 괄호 {brace_count}개 추가")

            return json_str
        except Exception as e:
            self.logger.error(f"JSON 복구 중 오류: {e}")
            return None

    def _save_checkpoint(
        self,
        checkpoint_file: Path,
        chunk_graphs: list,
        last_completed_idx: int
    ):
        """체크포인트 저장 (JSON 직렬화 가능한 데이터만 저장)"""
        try:
            import json

            # chunk_graphs를 JSON 직렬화 가능한 형태로 변환
            serializable_graphs = []
            for graph in chunk_graphs:
                if isinstance(graph, dict):
                    # 이미 dict이면 그대로 사용
                    serializable_graphs.append(graph)
                elif hasattr(graph, '__dict__'):
                    # 객체면 __dict__ 사용 (주의: 재귀적으로 변환 필요할 수 있음)
                    # 하지만 체크포인트는 나중에 병합할 수 있는 graph 형태만 저장하면 됨
                    # graph 구조: {"nodes": [...], "edges": [...]}
                    if hasattr(graph, 'get'):
                        serializable_graphs.append(graph)
                    else:
                        self.logger.debug(f"⚠️ 직렬화 불가능한 객체 건너뛰기: {type(graph)}")
                        continue

            checkpoint = {
                "last_completed_idx": last_completed_idx,
                "chunk_graphs": serializable_graphs,
                "timestamp": datetime.now().isoformat()
            }

            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, ensure_ascii=False, indent=2, default=str)

            self.logger.debug(f"💾 체크포인트 저장: {last_completed_idx + 1}개 청크 완료 ({len(serializable_graphs)}개 그래프)")
        except Exception as e:
            self.logger.warning(f"⚠️ 체크포인트 저장 실패: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())

    def _assign_uuids_to_graph(self, kg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Knowledge Graph의 모든 노드와 엣지에 UUID 할당

        LLM이 생성한 ID(n1, n2, e1 등)를 UUID로 변환하여 전역 고유성 보장
        """
        nodes = kg_data.get("nodes", [])
        edges = kg_data.get("edges", [])

        # 원본 ID → UUID 매핑
        id_mapping = {}

        # 1. 노드에 UUID 할당
        for node in nodes:
            old_id = node.get("id", "")
            new_id = str(uuid.uuid4())
            node["id"] = new_id
            id_mapping[old_id] = new_id

        # 2. 엣지에 UUID 할당 및 source/target 업데이트
        for edge in edges:
            # 엣지 ID를 UUID로 변경
            edge["id"] = str(uuid.uuid4())

            # source/target을 UUID로 매핑
            old_source = edge.get("source", "")
            old_target = edge.get("target", "")

            edge["source"] = id_mapping.get(old_source, str(uuid.uuid4()))
            edge["target"] = id_mapping.get(old_target, str(uuid.uuid4()))

        return {
            "nodes": nodes,
            "edges": edges
        }

    def _enrich_kg_with_metadata(
        self,
        kg_data: Dict[str, Any],
        file_path: str,
        domain: str,
        structure_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Knowledge Graph에 메타데이터 추가"""
        # UUID 할당 먼저 수행
        kg_data = self._assign_uuids_to_graph(kg_data)

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
        format: str = "json",
        target_db: str = "memgraph"
    ) -> Dict[str, str]:
        """
        Knowledge Graph를 파일로 저장

        Args:
            kg_result: Knowledge Graph 결과
            output_dir: 출력 디렉토리
            format: 저장 형식 (json, cypher, graphml, all)
            target_db: Cypher 대상 DB (memgraph, neo4j)

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
                cypher_content = self._generate_cypher_queries(kg_result, target_db=target_db)
                with cypher_path.open('w', encoding='utf-8') as f:
                    f.write(cypher_content)
                saved_files["cypher"] = str(cypher_path)
                self.logger.info(f"📝 Knowledge Graph Cypher 저장 (대상: {target_db}): {cypher_path}")

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

    def _generate_cypher_queries(self, kg_result: Dict[str, Any], target_db: str = "memgraph") -> str:
        """Cypher CREATE 쿼리 생성 (Neo4j/Memgraph 호환)

        Args:
            kg_result: Knowledge Graph 결과
            target_db: 대상 DB (memgraph, neo4j)

        Returns:
            Cypher 쿼리 문자열
        """
        queries = []
        queries.append("// Knowledge Graph Cypher Queries")
        queries.append(f"// Target Database: {target_db.upper()}")
        queries.append(f"// Generated: {datetime.now().isoformat()}")
        queries.append(f"// Total Nodes: {len(kg_result.get('graph', {}).get('nodes', []))}")
        queries.append(f"// Total Edges: {len(kg_result.get('graph', {}).get('edges', []))}\n")

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
        max_chunk_tokens: int = 16000,  # 기본값 증가: 청크 수 감소
        output_dir: Optional[Path] = None,
        extraction_level: str = "standard",
        fail_fast: bool = False,
        force_restart: bool = False  # 변경: resume → force_restart (기본값은 체크포인트 재개)
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
            fail_fast: 청크 오류 시 즉시 중단 (True: 개발/테스트 모드, False: 운용 모드)
            force_restart: 체크포인트 무시하고 처음부터 시작 (True: 무시, False: 재개 - 기본값)

        Returns:
            병합된 완전한 Knowledge Graph
        """
        try:
            total_start = time.time()

            # 파일명에서 문서 제목 추출
            document_title = Path(file_path).stem  # 확장자 제외한 파일명
            self.logger.info(f"🔍 청킹 기반 Full KG 생성 시작: {document_title}")

            # 1. 문서 청킹
            chunking_start = time.time()
            from .document_chunker import StructuralChunker
            chunker = StructuralChunker()

            # 문서 구조 분석 및 청킹
            document_tree = chunker.analyzer.analyze_structure(text)
            chunker_level = chunker.determine_chunking_level(len(text), document_tree)
            chunks = chunker.create_chunks(
                document_tree,
                chunk_level=chunker_level,
                max_chunk_tokens=max_chunk_tokens  # API 파라미터 전달
            )

            chunking_duration = time.time() - chunking_start
            self.logger.info(f"📄 문서를 {len(chunks)}개 청크로 분할 완료 (소요시간: {chunking_duration:.2f}초)")

            # 2. 각 청크에서 KG 추출
            chunk_graphs = []
            total_tokens_used = {"input": 0, "output": 0, "total": 0}  # 전체 토큰 사용량 누적

            # 청크 디버그 디렉토리 생성
            if output_dir:
                chunk_debug_dir = Path(output_dir) / "chunk_kg_debug"
                chunk_debug_dir.mkdir(parents=True, exist_ok=True)
            else:
                chunk_debug_dir = None

            # 체크포인트 파일 경로
            checkpoint_file = None
            start_idx = 0

            if chunk_debug_dir:
                checkpoint_file = chunk_debug_dir / "checkpoint.json"

                # force_restart=False이고 체크포인트가 있으면 재개 (기본 동작)
                if not force_restart and checkpoint_file.exists():
                    try:
                        import json
                        with open(checkpoint_file, 'r', encoding='utf-8') as f:
                            checkpoint = json.load(f)

                        # 이전 청크 결과 로드
                        chunk_graphs = checkpoint.get('chunk_graphs', [])
                        start_idx = checkpoint.get('last_completed_idx', 0) + 1

                        self.logger.info(f"🔄 체크포인트에서 재개: {start_idx}/{len(chunks)} 청크부터 시작 ({len(chunk_graphs)}개 청크 이미 완료)")
                    except Exception as e:
                        self.logger.warning(f"⚠️ 체크포인트 로드 실패: {e}, 처음부터 시작")
                        start_idx = 0
                        chunk_graphs = []
                elif force_restart and checkpoint_file.exists():
                    # force_restart=True인 경우 기존 체크포인트 삭제
                    try:
                        checkpoint_file.unlink()
                        self.logger.info(f"🗑️ force_restart=True: 기존 체크포인트 삭제, 처음부터 시작")
                    except Exception as e:
                        self.logger.warning(f"⚠️ 체크포인트 삭제 실패: {e}")

            for idx, chunk_group in enumerate(chunks):
                chunk_id = f"chunk_{idx+1:03d}"

                # 이미 처리된 청크는 건너뛰기
                if idx < start_idx:
                    self.logger.info(f"⏩ 청크 {idx+1}/{len(chunks)} 건너뛰기 (이미 완료)")
                    continue

                chunk_text = chunk_group.get_total_content()
                parent_context = chunk_group.parent_context or "문서 루트"

                self.logger.info(f"🔍 청크 {idx+1}/{len(chunks)} KG 추출 중... ({len(chunk_text):,}자)")

                try:
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

                    # 토큰 사용량 누적
                    chunk_tokens = kg_data.get("tokens", {})
                    total_tokens_used["input"] += chunk_tokens.get("input", 0)
                    total_tokens_used["output"] += chunk_tokens.get("output", 0)
                    total_tokens_used["total"] += chunk_tokens.get("total", 0)

                    # kg_data가 None이면 이미 예외가 발생했을 것이므로 여기까지 오지 않음
                    chunk_graphs.append({
                        "chunk_id": chunk_id,
                        "graph": kg_data,
                        "level": chunk_group.level,
                        "nodes_in_chunk": chunk_group.nodes
                    })

                    # 체크포인트 저장 (성공한 경우에만)
                    if checkpoint_file:
                        self._save_checkpoint(checkpoint_file, chunk_graphs, idx)

                except Exception as e:
                    if fail_fast:
                        # 개발/테스트 모드: 체크포인트 저장 후 즉시 중단
                        if checkpoint_file:
                            self._save_checkpoint(checkpoint_file, chunk_graphs, idx - 1)
                        self.logger.error(f"❌ {chunk_id} KG 추출 실패 (fail_fast=True, 즉시 중단)")
                        self.logger.info(f"💾 체크포인트 저장됨: 같은 옵션으로 재실행하면 자동 재개됨 (force_restart=true로 처음부터 시작 가능)")
                        raise
                    else:
                        # 운용 모드: 건너뛰고 계속 (기본값)
                        self.logger.error(f"⚠️ {chunk_id} KG 추출 실패: {e}")
                        self.logger.warning(f"⏭️ {chunk_id} 건너뛰고 다음 청크 처리 계속... (fail_fast=False)")
                        # 실패한 청크는 빈 그래프로 추가
                        chunk_graphs.append({
                            "chunk_id": chunk_id,
                            "graph": {"nodes": [], "edges": []},
                            "level": chunk_group.level,
                            "nodes_in_chunk": chunk_group.nodes,
                            "error": str(e)
                        })

                        # 체크포인트 저장 (실패한 경우에도)
                        if checkpoint_file:
                            self._save_checkpoint(checkpoint_file, chunk_graphs, idx)

            # 3. 성공한 청크 확인 (운용 모드에서만)
            if not fail_fast:
                successful_chunks = [cg for cg in chunk_graphs if not cg.get("error")]
                failed_chunks = [cg for cg in chunk_graphs if cg.get("error")]

                if failed_chunks:
                    self.logger.warning(f"⚠️ {len(failed_chunks)}개 청크 처리 실패")
                    for fc in failed_chunks:
                        self.logger.warning(f"  - {fc['chunk_id']}: {fc.get('error', 'Unknown error')}")

                if not successful_chunks:
                    raise ValueError(f"모든 청크 처리 실패 ({len(chunks)}개 청크 중 0개 성공)")

                self.logger.info(f"✅ {len(successful_chunks)}/{len(chunks)} 청크 성공적으로 처리됨")
            else:
                # 개발/테스트 모드에서는 모든 청크가 성공했다고 가정 (실패 시 위에서 이미 raise)
                successful_chunks = chunk_graphs
                failed_chunks = []

            # 4. 모든 청크 완료 시 체크포인트 삭제
            if checkpoint_file and checkpoint_file.exists():
                try:
                    checkpoint_file.unlink()
                    self.logger.info(f"🗑️ 모든 청크 완료: 체크포인트 삭제")
                except Exception as e:
                    self.logger.warning(f"⚠️ 체크포인트 삭제 실패: {e}")

            # 5. 청크별 KG 병합
            merge_start = time.time()
            self.logger.info(f"🔗 {len(chunk_graphs)}개 청크 KG 병합 중...")
            merged_kg = self._merge_chunk_graphs(chunk_graphs)
            merge_duration = time.time() - merge_start
            self.logger.info(f"✅ 청크 병합 완료 (소요시간: {merge_duration:.2f}초)")

            # 6. 메타데이터 추가
            result = self._enrich_kg_with_metadata(
                merged_kg,
                file_path,
                domain,
                structure_info
            )

            # 청킹 정보 및 시간 정보 추가
            total_duration = time.time() - total_start
            result["chunking_stats"] = {
                "total_chunks": len(chunks),
                "successful_extractions": len(successful_chunks),
                "failed_extractions": len(failed_chunks),
                "max_chunk_tokens": max_chunk_tokens
            }

            result["performance_metrics"] = {
                "total_duration": total_duration,
                "chunking_duration": chunking_duration,
                "extraction_duration": total_duration - chunking_duration - merge_duration,
                "merge_duration": merge_duration,
                "average_chunk_duration": (total_duration - chunking_duration - merge_duration) / len(chunks) if chunks else 0,
                "total_tokens_used": total_tokens_used
            }

            self.logger.info(
                f"✅ Full KG 생성 완료: "
                f"{result['stats']['entity_count']}개 엔티티, "
                f"{result['stats']['relationship_count']}개 관계 "
                f"(총 소요시간: {total_duration:.2f}초, "
                f"청크당 평균: {result['performance_metrics']['average_chunk_duration']:.2f}초, "
                f"총 토큰: 입력 {total_tokens_used['input']:,} + 출력 {total_tokens_used['output']:,} = {total_tokens_used['total']:,})"
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

            chunk_total_start = time.time()

            # === Phase 1: 엔티티만 추출 ===
            phase1_start = time.time()

            # 추출 레벨에 따라 프롬프트 선택
            level_prompts = {
                "brief": KnowledgeGraphPrompts.PHASE1_ENTITY_BRIEF,
                "standard": KnowledgeGraphPrompts.PHASE1_ENTITY_STANDARD,
                "deep": KnowledgeGraphPrompts.PHASE1_ENTITY_DEEP
            }

            entity_template = level_prompts.get(extraction_level.lower(), level_prompts["standard"])

            self.logger.info(f"🔍 {chunk_id} Phase 1: 엔티티 추출 시작... (레벨: {extraction_level}, 문서: {document_title})")

            entity_prompt = entity_template.format(text=chunk_text, document_title=document_title)

            # 디버그: Phase 1 프롬프트 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase1_prompt.txt").write_text(entity_prompt, encoding='utf-8')

            # Phase 1 LLM 호출
            llm_call_start = time.time()
            phase1_response = self._call_llm_for_kg(entity_prompt, llm_config)
            llm_call_duration = time.time() - llm_call_start

            if not phase1_response.get("success"):
                error_msg = f"{chunk_id} Phase 1 LLM 호출 실패: {phase1_response.get('error')}"
                self.logger.error(f"❌ {error_msg}")
                if debug_dir:
                    (debug_dir / f"{chunk_id}_phase1_error.txt").write_text(phase1_response.get('error', ''), encoding='utf-8')
                raise ValueError(error_msg)

            phase1_raw = phase1_response.get("response", "")
            phase1_tokens = phase1_response.get("tokens", {})

            # 디버그: Phase 1 응답 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase1_response.txt").write_text(phase1_raw, encoding='utf-8')

            # Phase 1 파싱
            parse_start = time.time()
            entities_data = self._parse_kg_response(phase1_raw)
            entities = entities_data.get('entities', entities_data.get('nodes', []))
            parse_duration = time.time() - parse_start

            if not entities:
                error_msg = f"{chunk_id} Phase 1 실패: 엔티티가 추출되지 않았습니다"
                self.logger.error(f"❌ {error_msg}")
                if debug_dir:
                    (debug_dir / f"{chunk_id}_phase1_parse_error.txt").write_text(
                        f"{error_msg}\n\nResponse: {phase1_raw[:1000]}", encoding='utf-8'
                    )
                raise ValueError(error_msg)

            phase1_duration = time.time() - phase1_start
            self.logger.info(
                f"✅ {chunk_id} Phase 1 완료: {len(entities)}개 엔티티 추출 "
                f"(LLM: {llm_call_duration:.2f}초, 파싱: {parse_duration:.2f}초, 전체: {phase1_duration:.2f}초, "
                f"토큰: 입력 {phase1_tokens.get('input', 0):,} + 출력 {phase1_tokens.get('output', 0):,} = 총 {phase1_tokens.get('total', 0):,})"
            )

            # === Phase 2: 관계만 추출 ===
            phase2_start = time.time()
            self.logger.info(f"🔗 {chunk_id} Phase 2: 관계 추출 시작...")

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
            llm_call_start = time.time()
            phase2_response = self._call_llm_for_kg(relation_prompt, llm_config)
            llm_call_duration = time.time() - llm_call_start

            if not phase2_response.get("success"):
                error_msg = f"{chunk_id} Phase 2 LLM 호출 실패: {phase2_response.get('error')}"
                self.logger.error(f"❌ {error_msg}")
                if debug_dir:
                    (debug_dir / f"{chunk_id}_phase2_error.txt").write_text(phase2_response.get('error', ''), encoding='utf-8')
                raise ValueError(error_msg)

            phase2_raw = phase2_response.get("response", "")
            phase2_tokens = phase2_response.get("tokens", {})

            # 디버그: Phase 2 응답 저장
            if debug_dir:
                (debug_dir / f"{chunk_id}_phase2_response.txt").write_text(phase2_raw, encoding='utf-8')

            # Phase 2 파싱
            parse_start = time.time()
            relations_data = self._parse_kg_response(phase2_raw)
            relationships = relations_data.get('relationships', relations_data.get('edges', []))
            parse_duration = time.time() - parse_start

            phase2_duration = time.time() - phase2_start
            self.logger.info(
                f"✅ {chunk_id} Phase 2 완료: {len(relationships)}개 관계 추출 "
                f"(LLM: {llm_call_duration:.2f}초, 파싱: {parse_duration:.2f}초, 전체: {phase2_duration:.2f}초, "
                f"토큰: 입력 {phase2_tokens.get('input', 0):,} + 출력 {phase2_tokens.get('output', 0):,} = 총 {phase2_tokens.get('total', 0):,})"
            )

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

            chunk_total_duration = time.time() - chunk_total_start

            # 전체 토큰 사용량 계산
            total_input_tokens = phase1_tokens.get('input', 0) + phase2_tokens.get('input', 0)
            total_output_tokens = phase1_tokens.get('output', 0) + phase2_tokens.get('output', 0)
            total_tokens = phase1_tokens.get('total', 0) + phase2_tokens.get('total', 0)

            self.logger.info(
                f"✅ {chunk_id} 2-Phase 추출 완료: "
                f"{len(entities)}개 엔티티, {len(relationships)}개 관계 "
                f"(전체 소요시간: {chunk_total_duration:.2f}초, "
                f"총 토큰: 입력 {total_input_tokens:,} + 출력 {total_output_tokens:,} = {total_tokens:,})"
            )

            # 토큰 정보를 kg_data에 추가
            kg_data["tokens"] = {
                "input": total_input_tokens,
                "output": total_output_tokens,
                "total": total_tokens
            }

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
        """여러 청크의 KG를 하나로 병합 (UUID 사용으로 전역 고유성 보장)"""
        merged_nodes = []
        merged_edges = []
        node_id_map = {}  # 원본 ID → UUID 매핑
        node_dedup_map = {}  # (type, name) → UUID 매핑 (중복 제거용)

        for chunk_data in chunk_graphs:
            chunk_id = chunk_data["chunk_id"]
            graph = chunk_data["graph"]

            # 노드 병합 (UUID 사용으로 전역 고유성 보장)
            for node in graph.get("nodes", []):
                original_id = node["id"]

                # 동일한 엔티티 중복 체크 (이름과 타입이 같으면 병합)
                node_key = (node.get("type"), node.get("properties", {}).get("name"))

                if node_key in node_dedup_map:
                    # 기존 노드 UUID 재사용 (중복 제거)
                    uuid_id = node_dedup_map[node_key]
                    node_id_map[original_id] = uuid_id
                else:
                    # 새 UUID 생성
                    uuid_id = str(uuid.uuid4())
                    node["id"] = uuid_id
                    merged_nodes.append(node)
                    node_id_map[original_id] = uuid_id
                    node_dedup_map[node_key] = uuid_id

            # 관계 병합 (UUID 사용)
            for edge in graph.get("edges", []):
                # 원본 ID를 UUID로 변환
                source = edge.get("source", "")
                target = edge.get("target", "")

                # chunk_id 접두사 제거 후 매핑
                source_base = source.split("_", 1)[-1] if "_" in source else source
                target_base = target.split("_", 1)[-1] if "_" in target else target

                new_source = node_id_map.get(source_base, node_id_map.get(source, str(uuid.uuid4())))
                new_target = node_id_map.get(target_base, node_id_map.get(target, str(uuid.uuid4())))

                edge["source"] = new_source
                edge["target"] = new_target
                edge["id"] = str(uuid.uuid4())  # 관계도 UUID 사용

                merged_edges.append(edge)

        self.logger.info(
            f"🔗 병합 완료: {len(merged_nodes)}개 엔티티 (중복 제거 후), "
            f"{len(merged_edges)}개 관계"
        )

        return {
            "nodes": merged_nodes,
            "edges": merged_edges
        }
