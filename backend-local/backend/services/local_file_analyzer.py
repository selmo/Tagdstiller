"""LLM-only document structure analyzer for the backend-local service."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from sqlalchemy.orm import Session

from prompts.templates import DocumentStructurePrompts
from services.config_service import ConfigService
from utils.llm_logger import log_prompt_and_response

try:  # pragma: no cover - optional dependency
    from langchain_ollama import OllamaLLM  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    OllamaLLM = None


class LLMJsonError(RuntimeError):
    """Raised when the LLM response cannot be parsed as JSON."""

    def __init__(self, message: str, raw_response: str):
        super().__init__(message)
        self.raw_response = raw_response


class LocalFileAnalyzer:
    """Minimal analyzer that delegates structure extraction to an LLM."""

    def __init__(self, db: Session):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def analyze_document_structure_with_llm(
        self,
        text: str,
        file_path: str,
        file_extension: str,
        overrides: Optional[Dict[str, Any]] = None,
        use_multistep: bool = False,  # 다단계 대화 방식 사용 여부
    ) -> Dict[str, Any]:
        overrides = overrides or {}
        provider = overrides.get("provider") or ConfigService.get_config_value(self.db, "LLM_PROVIDER", "ollama")
        if not overrides.get("enabled") and not ConfigService.get_bool_config(self.db, "ENABLE_LLM_EXTRACTION", False):
            return self._fail_result("LLM extraction disabled", "")

        timeout_override = overrides.get("timeout")
        ollama_timeout_default = ConfigService.get_int_config(self.db, "OLLAMA_TIMEOUT", 120)

        if provider == "ollama":
            if OllamaLLM is None:
                return self._fail_result("langchain_ollama is not installed", "")
            base_url = overrides.get("base_url") or ConfigService.get_config_value(self.db, "OLLAMA_BASE_URL", "http://localhost:11434")
            model_name = overrides.get("model") or ConfigService.get_config_value(self.db, "OLLAMA_MODEL", "llama3.2")
            timeout = timeout_override or ollama_timeout_default
            fetch = lambda prompt: self._call_ollama(prompt, base_url, model_name, timeout)
            base_dir_provider = "ollama"
            base_url_meta = base_url
        elif provider == "openai":
            conf = {**ConfigService.get_openai_config(self.db), **overrides}
            if timeout_override is not None:
                conf["timeout"] = timeout_override
            conf.setdefault("timeout", 120)
            fetch = lambda prompt: self._call_openai_chat(prompt, conf)
            base_dir_provider = "openai"
            base_url_meta = conf.get("base_url", "https://api.openai.com/v1")
            model_name = conf.get("model", "")
        elif provider == "gemini":
            conf = {**ConfigService.get_gemini_config(self.db), **overrides}
            if timeout_override is not None:
                conf["timeout"] = timeout_override
            conf.setdefault("timeout", 120)
            conf.setdefault("response_mime_type", "application/json")
            fetch = lambda prompt: self._call_gemini_generate(prompt, conf)
            base_dir_provider = "gemini"
            base_url_meta = conf.get("base_url", "https://generativelanguage.googleapis.com")
            model_name = conf.get("model", "")
        else:
            return self._fail_result(f"Unsupported provider: {provider}", "")

        # max_tokens 기반으로 문서 크기 계산
        max_tokens = conf.get("max_tokens", 8000)
        # 프롬프트 템플릿과 응답을 위한 토큰 예약 (대략 2000 토큰)
        reserved_tokens = 2000
        available_tokens = max(max_tokens - reserved_tokens, 1000)  # 최소 1000 토큰 보장
        # 토큰을 문자 수로 변환 (한국어 기준 약 1.5자/토큰)
        max_chars = int(available_tokens * 1.5)

        truncated_text = text[:max_chars] if len(text) > max_chars else text
        file_info = {
            "filename": Path(file_path).name,
            "extension": file_extension,
            "size": len(text),
            "truncated_size": len(truncated_text),
        }
        prompt_template = (
            DocumentStructurePrompts.STRUCTURE_ANALYSIS_LLM_GEMINI_FLASH25
            if provider == "gemini" and isinstance(model_name, str) and "2.5" in model_name
            else DocumentStructurePrompts.STRUCTURE_ANALYSIS_LLM
        )
        # 다단계 대화 방식 사용 여부 확인
        if use_multistep:
            self.logger.info("🔄 다단계 대화 방식으로 분석 진행")
            try:
                return self._analyze_with_multistep_conversation(
                    text=truncated_text,
                    file_info=file_info,
                    fetch=fetch,
                    model_name=model_name,
                    base_dir_provider=base_dir_provider,
                    base_url_meta=base_url_meta,
                    file_path=file_path,
                    overrides=overrides
                )
            except Exception as e:
                self.logger.error(f"❌ 다단계 분석 실패: {e}, 일반 방식으로 폴백")
                # 폴백: 일반 방식으로 진행

        # 일반 방식 (단일 프롬프트)
        prompt = prompt_template.format(
            file_info=json.dumps(file_info, ensure_ascii=False, indent=2),
            text=truncated_text,
        )

        try:
            response_text, raw_response = fetch(prompt)
        except LLMJsonError as exc:
            return self._fail_result(str(exc), exc.raw_response)
        except Exception as exc:  # pragma: no cover - transport errors
            self.logger.error("❌ LLM 호출 실패: %s", exc)
            return self._fail_result(str(exc), "")

        log_prompt_and_response(
            label="document_structure_analysis",
            provider=base_dir_provider,
            model=model_name,
            prompt=prompt,
            response=response_text,
            logger=self.logger,
            base_dir=self._default_output_dir(file_path),
            meta={
                "base_url": base_url_meta,
                "temperature": overrides.get("temperature", 0.2),
                "file_extension": file_extension,
                "text_length": len(text),
                "truncated_length": len(truncated_text),
            },
            raw_response=raw_response,
        )

        # JSON 파싱 시도 with 에러 처리
        try:
            json_response = json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ LLM 응답 JSON 파싱 실패: {e}")
            self.logger.error(f"   오류 위치: line {e.lineno}, column {e.colno}, char {e.pos}")
            self.logger.error(f"   응답 길이: {len(response_text)} 문자")

            # 토큰 제한 초과 여부 확인 (raw_response에서)
            is_token_limit = False
            if "MAX_TOKENS" in raw_response or "max_tokens" in raw_response.lower():
                is_token_limit = True
                self.logger.error(f"   ⚠️ 원인: 토큰 제한 초과로 응답이 잘린 것으로 추정됨")

            # 응답 텍스트의 마지막 부분 로깅 (디버깅용)
            if len(response_text) > 200:
                self.logger.error(f"   응답 끝부분: ...{response_text[-200:]}")

            # 잘린 JSON 부분 복구 시도
            if is_token_limit and response_text.strip():
                self.logger.info("🔧 잘린 JSON 복구 시도 중...")
                recovered_json = self._try_recover_truncated_json(response_text)
                if recovered_json:
                    self.logger.info("✅ 부분 JSON 복구 성공")
                    return {
                        "analysis_method": "llm_partial_recovery",
                        "llm_success": True,
                        "llm_model": model_name,
                        "llm_analysis": recovered_json,
                        "warning": "토큰 제한으로 응답이 잘렸으나 부분 복구됨"
                    }

            return self._fail_result(
                f"LLM 응답이 유효한 JSON이 아닙니다: {str(e)}" +
                (" (토큰 제한 초과로 인한 잘림 가능성)" if is_token_limit else ""),
                response_text
            )

        return {
            "analysis_method": "llm_only",
            "llm_success": True,
            "llm_model": model_name,
            "llm_analysis": json_response,
        }

    # ------------------------------------------------------------------
    # Multi-step conversation helpers
    # ------------------------------------------------------------------
    def _analyze_with_multistep_conversation(
        self,
        text: str,
        file_info: Dict[str, Any],
        fetch: callable,
        model_name: str,
        base_dir_provider: str,
        base_url_meta: str,
        file_path: str,
        overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        다단계 대화 방식으로 문서 분석

        전략:
        1. 전체 구조 개요 요청 (작은 응답)
        2. 각 섹션별 상세 분석 요청 (여러 번의 작은 응답)
        3. 모든 응답 병합
        """
        self.logger.info("📝 1단계: 문서 구조 개요 추출")

        # Step 1: 문서 구조 개요만 추출
        overview_prompt = f"""다음 문서의 구조를 **간략하게** 분석하세요.

파일 정보:
{json.dumps(file_info, ensure_ascii=False, indent=2)}

텍스트:
{text[:3000]}... (전체 {len(text)}자)

다음 JSON 형식으로만 응답하세요:
{{
  "documentType": "문서 유형",
  "mainSections": ["섹션1", "섹션2", "섹션3"],
  "estimatedPageCount": 숫자,
  "primaryLanguage": "ko/en"
}}
"""

        overview_text, overview_raw = fetch(overview_prompt)
        overview_json = json.loads(self._strip_markers(overview_text))

        self.logger.info(f"✅ 구조 개요: {len(overview_json.get('mainSections', []))}개 섹션 발견")

        # Step 2: 각 섹션별 키워드 추출 (분할 정복)
        sections = overview_json.get("mainSections", [])
        section_analyses = []

        for idx, section_name in enumerate(sections[:5]):  # 최대 5개 섹션
            self.logger.info(f"📝 {idx+1}단계: '{section_name}' 섹션 분석 중...")

            section_prompt = f"""문서에서 "{section_name}" 섹션의 핵심 키워드 5개만 추출하세요.

텍스트:
{text[:5000]}

다음 JSON 형식으로만 응답하세요:
{{
  "section": "{section_name}",
  "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
}}
"""

            try:
                section_text, section_raw = fetch(section_prompt)
                section_json = json.loads(self._strip_markers(section_text))
                section_analyses.append(section_json)
                self.logger.info(f"✅ '{section_name}' 분석 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ '{section_name}' 분석 실패: {e}")
                continue

        # Step 3: 결과 병합
        merged_analysis = {
            "structureAnalysis": {
                "documentType": overview_json.get("documentType"),
                "language": overview_json.get("primaryLanguage"),
                "sections": overview_json.get("mainSections", []),
                "estimatedPages": overview_json.get("estimatedPageCount", 0)
            },
            "keywordsBySection": section_analyses,
            "allKeywords": []
        }

        # 모든 키워드 통합
        for section_analysis in section_analyses:
            merged_analysis["allKeywords"].extend(section_analysis.get("keywords", []))

        self.logger.info(f"✅ 다단계 분석 완료: {len(section_analyses)}개 섹션, {len(merged_analysis['allKeywords'])}개 키워드")

        return {
            "analysis_method": "llm_multistep",
            "llm_success": True,
            "llm_model": model_name,
            "llm_analysis": merged_analysis,
            "steps_completed": len(section_analyses) + 1
        }

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------
    def _call_gemini_stream(
        self, base_url: str, model: str, api_key: str, payload: Dict[str, Any], conf: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Gemini 스트리밍 API 호출 - 응답을 청크로 받아서 합침

        장점:
        - 토큰 제한을 넘어도 전체 응답 수신 가능
        - 진행 상황 실시간 확인 가능
        """
        import time

        url = f"{base_url}/v1beta/{model}:streamGenerateContent?key={api_key}&alt=sse"

        self.logger.info("📡 Gemini 스트리밍 API 호출 시작...")

        # 재시도 로직
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=conf.get("timeout", 180),  # 스트리밍은 더 긴 타임아웃
                    stream=True  # 스트리밍 활성화
                )
                response.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    self.logger.warning(f"⚠️ Gemini Stream API 503 에러, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

        # 스트리밍 응답 처리
        accumulated_text = []
        accumulated_responses = []
        total_chunks = 0
        last_log_time = time.time()

        for line in response.iter_lines():
            if not line:
                continue

            line_str = line.decode('utf-8')

            # SSE 형식 파싱: "data: {JSON}"
            if line_str.startswith('data: '):
                json_str = line_str[6:]  # "data: " 제거
                try:
                    chunk_data = json.loads(json_str)
                    accumulated_responses.append(chunk_data)

                    # 텍스트 청크 추출
                    for candidate in chunk_data.get("candidates", []):
                        parts = candidate.get("content", {}).get("parts", [])
                        for part in parts:
                            if isinstance(part, dict) and "text" in part:
                                text_chunk = part["text"]
                                accumulated_text.append(text_chunk)
                                total_chunks += 1

                                # 주기적 로깅 (1초마다)
                                current_time = time.time()
                                if current_time - last_log_time > 1.0:
                                    current_length = sum(len(t) for t in accumulated_text)
                                    self.logger.info(f"📥 스트리밍 수신 중... {total_chunks}개 청크, {current_length:,}자")
                                    last_log_time = current_time

                except json.JSONDecodeError as e:
                    self.logger.warning(f"⚠️ 스트리밍 청크 파싱 실패: {e}")
                    continue

        # 전체 응답 병합
        merged_text = "".join(accumulated_text).strip()

        # 토큰 사용량 로깅 (마지막 청크에서)
        if accumulated_responses:
            last_response = accumulated_responses[-1]
            usage_metadata = last_response.get("usageMetadata", {})
            if usage_metadata:
                prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                response_tokens = usage_metadata.get("candidatesTokenCount", 0)
                total_tokens = usage_metadata.get("totalTokenCount", 0)
                self.logger.info(
                    f"📊 Gemini 스트리밍 완료 - 프롬프트: {prompt_tokens}, 응답: {response_tokens}, 총합: {total_tokens}"
                )

        self.logger.info(f"✅ 스트리밍 완료: {total_chunks}개 청크 병합, 총 {len(merged_text):,}자")

        # raw_payload는 전체 응답 배열
        raw_payload = json.dumps(accumulated_responses, ensure_ascii=False)

        if not merged_text:
            raise LLMJsonError("Gemini streaming response is empty", raw_payload)

        return merged_text, raw_payload

    def _call_ollama(self, prompt: str, base_url: str, model: str, timeout: int) -> Tuple[str, str]:
        assert OllamaLLM is not None  # for type checkers
        client = OllamaLLM(base_url=base_url, model=model, timeout=timeout, temperature=0.2)
        response = client.invoke(prompt)
        return response, response

    def _call_openai_chat(self, prompt: str, conf: Dict[str, Any]) -> Tuple[str, str]:
        api_key = conf.get("api_key")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다")

        payload = {
            "model": conf.get("model", "gpt-3.5-turbo"),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": conf.get("max_tokens", 8000),
            "temperature": conf.get("temperature", 0.2),
        }
        response = requests.post(
            f"{conf.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=conf.get("timeout", 120),
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"]
        return text, text

    def _call_gemini_generate(self, prompt: str, conf: Dict[str, Any]) -> Tuple[str, str]:
        """
        Gemini API 호출 - 스트리밍 방식 우선 사용

        토큰 제한 초과 방지를 위해:
        1. streamGenerateContent API 사용 (응답을 청크로 수신)
        2. 일반 generateContent로 폴백 (스트리밍 실패 시)
        """
        import time

        api_key = conf.get("api_key")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다")

        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": conf.get("temperature", 0.2),
                "maxOutputTokens": conf.get("max_tokens", 8000),
            },
        }
        if conf.get("response_mime_type"):
            payload["generationConfig"]["responseMimeType"] = conf["response_mime_type"]

        base_url = conf.get('base_url', 'https://generativelanguage.googleapis.com')
        model = conf.get('model', 'models/gemini-1.5-pro')

        # 스트리밍 사용 여부 (기본값: True)
        use_streaming = conf.get("use_streaming", True)

        if use_streaming:
            # 스트리밍 API 시도
            try:
                return self._call_gemini_stream(base_url, model, api_key, payload, conf)
            except Exception as stream_error:
                self.logger.warning(f"⚠️ 스트리밍 API 실패, 일반 API로 폴백: {stream_error}")
                # 폴백: 일반 API 사용

        # 일반 API (non-streaming)
        url = f"{base_url}/v1beta/{model}:generateContent?key={api_key}"

        # 재시도 로직 (503 에러 대응)
        max_retries = 3
        retry_delay = 2  # 초

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, timeout=conf.get("timeout", 120))
                response.raise_for_status()
                break  # 성공하면 루프 종료
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503 and attempt < max_retries - 1:
                    self.logger.warning(f"⚠️ Gemini API 503 에러, {retry_delay}초 후 재시도 ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                else:
                    raise  # 마지막 시도거나 다른 에러면 예외 발생

        data = response.json()

        # 토큰 사용량 추출 및 로깅
        usage_metadata = data.get("usageMetadata", {})
        if usage_metadata:
            prompt_tokens = usage_metadata.get("promptTokenCount", 0)
            response_tokens = usage_metadata.get("candidatesTokenCount", 0)
            total_tokens = usage_metadata.get("totalTokenCount", 0)
            self.logger.info(
                f"📊 Gemini 토큰 사용량 - 프롬프트: {prompt_tokens}, 응답: {response_tokens}, 총합: {total_tokens}"
            )

        # finishReason 확인 (토큰 초과 감지)
        candidates = data.get("candidates", [])
        if candidates:
            finish_reason = candidates[0].get("finishReason", "")
            if finish_reason == "MAX_TOKENS":
                self.logger.warning("⚠️ 응답이 max_tokens 제한으로 잘렸습니다 (finishReason: MAX_TOKENS)")
                # 토큰 제한 초과 정보를 raw_payload에 표시
                max_tokens_exceeded = True
            else:
                max_tokens_exceeded = False
        else:
            max_tokens_exceeded = False

        raw_payload = json.dumps(data, ensure_ascii=False)
        text_chunks: list[str] = []
        for candidate in data.get("candidates", []):
            parts = candidate.get("content", {}).get("parts", [])
            for part in parts:
                if isinstance(part, dict):
                    text_part = part.get("text")
                    if isinstance(text_part, str):
                        text_chunks.append(text_part)

        if not text_chunks:
            raise LLMJsonError("Gemini response contained no text parts", raw_payload)

        merged = "".join(text_chunks).strip()
        self.logger.info("✅ Gemini response length: %d characters", len(merged))
        if not merged:
            raise LLMJsonError("Gemini response text is empty", raw_payload)

        # 토큰 초과로 잘린 경우 경고 로그
        if max_tokens_exceeded:
            self.logger.warning(
                f"⚠️ 응답이 토큰 제한으로 잘렸을 가능성 있음 - "
                f"응답 길이: {len(merged)}자, max_tokens: {conf.get('max_tokens', 8000)}"
            )

        return merged, raw_payload

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        json_text = self._strip_markers(response)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Unable to parse JSON from LLM response: {exc}") from exc

    @staticmethod
    def _strip_markers(text: str) -> str:
        stripped = text.strip()
        stripped = re.sub(r'^```json\s*', '', stripped, flags=re.IGNORECASE)
        stripped = re.sub(r'^```\s*', '', stripped)
        stripped = re.sub(r'\s*```$', '', stripped)
        if stripped.startswith('\ufeff'):
            stripped = stripped.lstrip('\ufeff')
        return stripped

    def _default_output_dir(self, file_path: str) -> str:
        try:
            from services.document_parser_service import DocumentParserService

            parser_service = DocumentParserService()
            absolute_path = Path(file_path) if Path(file_path).is_absolute() else Path.cwd() / file_path
            output_dir = parser_service.get_output_directory(absolute_path)
            return str(output_dir)
        except Exception:
            return "llm_logs"

    def _try_recover_truncated_json(self, truncated_text: str) -> Optional[Dict[str, Any]]:
        """
        토큰 제한으로 잘린 JSON을 부분적으로 복구 시도

        전략:
        1. 유효한 JSON 객체가 완성된 부분까지 찾기
        2. 배열이나 객체가 닫히지 않은 경우 강제로 닫기
        3. 최소한의 필수 필드만이라도 추출
        """
        try:
            # 전략 1: 마지막 완전한 객체/배열까지만 파싱
            # 뒤에서부터 유효한 JSON이 끝나는 위치 찾기
            for i in range(len(truncated_text) - 1, -1, -1):
                try:
                    partial = truncated_text[:i+1]
                    # 닫히지 않은 중괄호/대괄호 수 세기
                    open_braces = partial.count('{') - partial.count('}')
                    open_brackets = partial.count('[') - partial.count(']')

                    # 닫히지 않은 것들을 강제로 닫기
                    closing = ']' * open_brackets + '}' * open_braces
                    fixed = partial + closing

                    parsed = json.loads(fixed)
                    self.logger.info(f"🔧 복구 성공: {i+1}/{len(truncated_text)} 문자까지 유효 (닫힌 괄호: {len(closing)}개)")
                    return parsed
                except json.JSONDecodeError:
                    # 100자 단위로 건너뛰며 시도 (성능 최적화)
                    if i % 100 != 0:
                        continue

            # 전략 2: structureAnalysis 필드만 추출 시도
            match = re.search(r'"structureAnalysis"\s*:\s*({[^}]*})', truncated_text, re.DOTALL)
            if match:
                try:
                    structure_part = json.loads(match.group(1) + '}')
                    self.logger.info("🔧 부분 복구: structureAnalysis 필드만 추출")
                    return {"structureAnalysis": structure_part}
                except:
                    pass

            self.logger.warning("⚠️ JSON 복구 실패: 유효한 부분을 찾을 수 없음")
            return None

        except Exception as e:
            self.logger.error(f"❌ JSON 복구 중 오류: {e}")
            return None

    def _fail_result(self, message: str, raw_response: str) -> Dict[str, Any]:
        self.logger.error("❌ LLM 구조 분석 실패: %s", message)
        if raw_response:
            self.logger.warning("⚠️ LLM 원본 응답 (200자): %s", raw_response[:200].replace("\n", " "))
        return {
            "analysis_method": "llm_failed",
            "llm_success": False,
            "llm_error": message,
            "llm_raw_response": raw_response,
        }


__all__ = ["LocalFileAnalyzer", "LLMJsonError"]
