"""LLM 기반 문서 구조 분석 전용 서비스."""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from sqlalchemy.orm import Session

from services.config_service import ConfigService
from prompts.templates import DocumentStructurePrompts
from utils.llm_logger import log_prompt_and_response

try:  # pragma: no cover - optional dependency
    from langchain_ollama import OllamaLLM  # type: ignore

    LANGCHAIN_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    LANGCHAIN_AVAILABLE = False


class LocalFileAnalyzer:
    """LLM 구조 분석 기능만 제공하는 경량 분석기."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def analyze_document_structure_with_llm(
        self,
        text: str,
        file_path: str,
        file_extension: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """LLM을 호출해 문서 구조 분석 결과(JSON)만 반환."""

        logger = logging.getLogger(__name__)
        overrides = overrides or {}

        llm_enabled = overrides.get("enabled")
        if llm_enabled is None:
            llm_enabled = ConfigService.get_bool_config(self.db, "ENABLE_LLM_EXTRACTION", False)
        if not llm_enabled:
            logger.warning("⚠️ LLM 구조 분석 비활성화 설정")
            return self._fallback_structure_analysis_with_llm_attempt(
                error_msg="LLM extraction is disabled",
            )

        provider = overrides.get("provider") or ConfigService.get_config_value(self.db, "LLM_PROVIDER", "ollama")
        timeout_override = overrides.get("timeout")
        ollama_timeout_default = ConfigService.get_int_config(self.db, "OLLAMA_TIMEOUT", 120)
        logger.info(f"🔍 LLM 기반 문서 구조 분석 시작 - provider={provider}")

        try:
            if provider == "ollama":
                if not LANGCHAIN_AVAILABLE:
                    raise RuntimeError("langchain_ollama 설치가 필요합니다")
                ollama_url = overrides.get("base_url") or ConfigService.get_config_value(
                    self.db, "OLLAMA_BASE_URL", "http://localhost:11434"
                )
                model_name = overrides.get("model") or ConfigService.get_config_value(
                    self.db, "OLLAMA_MODEL", "llama3.2"
                )
                ollama_timeout = timeout_override or ollama_timeout_default
                openai_conf = None
                gemini_conf = None
            elif provider == "openai":
                openai_conf = {**ConfigService.get_openai_config(self.db), **overrides}
                if timeout_override is not None:
                    openai_conf["timeout"] = timeout_override
                openai_conf.setdefault("timeout", 120)
                gemini_conf = None
                model_name = openai_conf.get("model")
                ollama_url = None
            elif provider == "gemini":
                gemini_conf = {**ConfigService.get_gemini_config(self.db), **overrides}
                if timeout_override is not None:
                    gemini_conf["timeout"] = timeout_override
                gemini_conf.setdefault("timeout", 120)
                openai_conf = None
                model_name = gemini_conf.get("model")
                gemini_conf.setdefault("response_mime_type", "application/json")
                ollama_url = None
            else:
                raise RuntimeError(f"지원하지 않는 provider: {provider}")
        except Exception as exc:  # pragma: no cover - config 오류
            logger.error(f"❌ LLM provider 설정 실패: {exc}")
            return self._fallback_structure_analysis_with_llm_attempt(error_msg=str(exc))

        logger.info(f"🔍 LLM 모델: {model_name}")

        # 텍스트 길이 제한
        max_text_length = 15000
        truncated_text = text[:max_text_length] if len(text) > max_text_length else text

        # 프롬프트 구성
        prompt_template = (
            DocumentStructurePrompts.STRUCTURE_ANALYSIS_LLM_GEMINI_FLASH25
            if provider == "gemini" and isinstance(model_name, str) and "2.5" in model_name
            else DocumentStructurePrompts.STRUCTURE_ANALYSIS_LLM
        )

        file_path_obj = Path(file_path) if isinstance(file_path, str) else file_path
        file_info = {
            "filename": file_path_obj.name,
            "extension": file_extension,
            "size": len(text),
            "truncated_size": len(truncated_text),
        }

        prompt = prompt_template.format(
            file_info=json.dumps(file_info, ensure_ascii=False, indent=2),
            text=truncated_text,
        )

        logger.info(f"📤 LLM 구조 분석 요청 (텍스트 길이: {len(truncated_text)}자)")

        # LLM 호출
        try:
            if provider == "ollama":
                ollama_client = OllamaLLM(
                    base_url=ollama_url,
                    model=model_name,
                    timeout=ollama_timeout,
                    temperature=0.2,
                )
                response = ollama_client.invoke(prompt)
                base_dir_provider = "ollama"
                base_url_meta = ollama_url
            elif provider == "openai":
                response = self._call_openai_chat(prompt, openai_conf)  # type: ignore[arg-type]
                base_dir_provider = "openai"
                base_url_meta = openai_conf.get("base_url", "https://api.openai.com/v1")  # type: ignore[union-attr]
            else:  # gemini
                response = self._call_gemini_generate(prompt, gemini_conf)  # type: ignore[arg-type]
                base_dir_provider = "gemini"
                base_url_meta = gemini_conf.get("base_url", "https://generativelanguage.googleapis.com")  # type: ignore[union-attr]
        except Exception as exc:
            logger.error(f"❌ LLM 호출 실패: {exc}")
            return self._fallback_structure_analysis_with_llm_attempt(error_msg=str(exc))

        logger.info(f"📥 LLM 응답 수신 (길이: {len(response)}자)")

        # 프롬프트/응답 로깅 (가능하면 동일 output 디렉터리 사용)
        base_dir = "tests/debug_outputs/llm"
        try:
            from services.document_parser_service import DocumentParserService

            parser_service = DocumentParserService()
            absolute_path = self.get_absolute_path(file_path)
            output_dir = parser_service.get_output_directory(absolute_path)
            base_dir = str(output_dir)
        except Exception:
            pass

        log_prompt_and_response(
            label="document_structure_analysis",
            provider=base_dir_provider,
            model=model_name,
            prompt=prompt,
            response=response,
            logger=logger,
            base_dir=base_dir,
            meta={
                "base_url": base_url_meta,
                "temperature": overrides.get("temperature", 0.2),
                "file_extension": file_extension,
                "text_length": len(text),
                "truncated_length": len(truncated_text),
            },
        )

        json_response = self._extract_json_from_response(response, logger)
        if not json_response:
            return self._fallback_structure_analysis_with_llm_attempt(
                error_msg="Unable to parse JSON from LLM response",
                raw_response=response,
            )

        return {
            "analysis_method": "llm_only",
            "llm_success": True,
            "llm_model": model_name,
            "llm_analysis": json_response,
        }

    # ------------------------------------------------------------------
    # Helper utilities
    # ------------------------------------------------------------------
    def get_absolute_path(self, file_path: str) -> Path:
        target_path = Path(file_path)
        return target_path if target_path.is_absolute() else (Path.cwd() / target_path).resolve()

    def _fallback_structure_analysis_with_llm_attempt(
        self,
        error_msg: str,
        raw_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        logging.getLogger(__name__).error(f"❌ LLM 구조 분석 실패: {error_msg}")
        return {
            "analysis_method": "llm_failed",
            "llm_success": False,
            "llm_error": error_msg,
            "llm_raw_response": raw_response or "",
        }

    # ---------------------- LLM HTTP helpers ----------------------
    def _call_openai_chat(self, prompt: str, conf: Dict[str, Any]) -> str:
        api_key = conf.get("api_key")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다")
        base_url = conf.get("base_url", "https://api.openai.com/v1")
        model = conf.get("model", "gpt-3.5-turbo")
        max_tokens = conf.get("max_tokens", 8000)
        temperature = conf.get("temperature", 0.2)
        timeout = conf.get("timeout", 120)

        url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _call_gemini_generate(self, prompt: str, conf: Dict[str, Any]) -> str:
        api_key = conf.get("api_key") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY가 설정되지 않았습니다")

        base_url = conf.get("base_url", "https://generativelanguage.googleapis.com")
        model = conf.get("model", "models/gemini-1.5-pro")
        max_tokens = conf.get("max_tokens", 8000)
        temperature = conf.get("temperature", 0.2)
        timeout = conf.get("timeout", 120)
        response_mime_type = conf.get("response_mime_type")

        url = f"{base_url}/v1beta/{model}:streamGenerateContent?key={api_key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if response_mime_type:
            payload["generationConfig"]["responseMimeType"] = response_mime_type

        logger = logging.getLogger(__name__)
        logger.debug(f"🔄 Gemini API 요청 - URL: {url}")
        logger.debug(f"📦 Payload 크기: {len(json.dumps(payload))} bytes")

        response = requests.post(url, json=payload, timeout=timeout, stream=True)
        response.raise_for_status()

        logger.debug(f"📥 Gemini 응답 상태 코드: {response.status_code}")

        full_text = []
        chunk_count = 0
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue

            # 디버그: 첫 100자 출력
            if chunk_count == 0:
                logger.debug(f"🔍 첫 번째 라인 (100자): {line[:100]}")

            # 중괄호로 시작하는 JSON 라인 처리
            if line.strip().startswith("{"):
                try:
                    data = json.loads(line)
                    chunk_count += 1
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if isinstance(part, dict) and "text" in part:
                                text_content = part["text"]
                                full_text.append(text_content)
                                logger.debug(f"✅ Chunk {chunk_count}: {len(text_content)} chars")
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON 파싱 실패: {e} - Line: {line[:50]}...")
                    continue
            # SSE 형식의 data: 접두사가 있는 경우
            elif line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                    chunk_count += 1
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if isinstance(part, dict) and "text" in part:
                                text_content = part["text"]
                                full_text.append(text_content)
                                logger.debug(f"✅ SSE Chunk {chunk_count}: {len(text_content)} chars")
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ SSE 파싱 실패: {e}")
                    continue

        result = "\n".join(full_text)
        logger.info(f"📊 Gemini 응답 총 길이: {len(result)} chars, 청크 수: {chunk_count}")

        if not result:
            logger.error("❌ Gemini API 응답이 비어있습니다")
            raise RuntimeError("Gemini API가 빈 응답을 반환했습니다")

        return result

    # ---------------------- JSON repair helpers ----------------------
    def _extract_json_from_response(self, response: str, logger: logging.Logger) -> Optional[Dict[str, Any]]:
        logger.info(f"🔍 JSON 추출 시작 - 응답 길이: {len(response)}자")
        logger.info(f"🔍 응답 시작부 (200자): {response[:200]!r}")
        logger.info(f"🔍 응답 끝부 (200자): {response[-200:]!r}")

        json_text = None
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```JSON\s*(.*?)\s*```',
            r'```\s*json\s*(.*?)\s*```',
            r'```\s*{.*?}\s*```',
        ]
        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                json_text = match.group(1).strip()
                logger.debug(f"📝 JSON 코드 블록 추출 (패턴: {pattern[:12]}…)")
                break

        if not json_text and "```" in response:
            match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                candidate = match.group(1).strip()
                if candidate.startswith('{') and candidate.endswith('}'):
                    json_text = candidate
                    logger.debug("📝 일반 코드 블록에서 JSON 추출")

        if not json_text:
            start_patterns = [
                r'\{\s*"documentInfo"',
                r'\{\s*"structureAnalysis"',
                r'\{\s*"coreContent"',
                r'\{\s*"metaInfo"',
            ]
            for pattern in start_patterns:
                match = re.search(pattern, response)
                if match:
                    json_text = response[match.start():]
                    break

        if not json_text:
            json_text = response.strip()
            logger.debug("📝 전체 응답을 JSON 후보로 사용")

        json_text = json_text.strip()
        json_text = re.sub(r'^```json\s*', '', json_text, flags=re.IGNORECASE)
        json_text = re.sub(r'^```\s*', '', json_text)
        json_text = re.sub(r'\s*```$', '', json_text)

        if json_text.startswith('\ufeff'):
            json_text = json_text.lstrip('\ufeff')
        json_text = json_text.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as exc:
            logger.warning(f"⚠️ JSON 파싱 실패(원본): {exc}")

        try:
            repaired = self._repair_json(json_text)
            return json.loads(repaired)
        except json.JSONDecodeError as exc:
            logger.warning(f"⚠️ JSON 파싱 실패(1차 보정): {exc}")

        try:
            aggressive = self._aggressive_json_repair(json_text)
            return json.loads(aggressive)
        except Exception as exc:
            logger.warning(f"⚠️ JSON 파싱 실패(2차 보정): {exc}")

        return None

    def analyze_document_structure(self, text: str, file_extension: str) -> Dict[str, Any]:
        """기본 문서 구조 분석 (LLM 없이)."""
        lines = text.split('\n')
        paragraphs = [p for p in text.split('\n\n') if p.strip()]

        # 섹션 탐지 (숫자나 대문자로 시작하는 줄)
        sections = []
        for i, line in enumerate(lines):
            if line and (line[0].isupper() or line[0].isdigit()):
                if len(line) < 100 and not line.endswith(('.', ',', ':')):
                    sections.append({
                        "line": i + 1,
                        "text": line.strip(),
                        "level": 1 if line[0].isdigit() else 2
                    })

        # 테이블 감지 (여러 개의 파이프 | 또는 탭이 있는 줄)
        tables = []
        for i, line in enumerate(lines):
            if line.count('|') > 2 or line.count('\t') > 2:
                tables.append({"line": i + 1, "text": line[:100]})

        return {
            "analysis_method": "basic",
            "structure": {
                "total_lines": len(lines),
                "total_paragraphs": len(paragraphs),
                "sections_detected": len(sections),
                "tables_detected": len(tables),
                "sections": sections[:10],  # 처음 10개만
                "tables": tables[:5],  # 처음 5개만
            },
            "metadata": {
                "file_extension": file_extension,
                "text_length": len(text),
                "average_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
            }
        }

    def _repair_json(self, json_text: str) -> str:
        json_text = re.sub(r'^```json\s*', '', json_text, flags=re.IGNORECASE)
        json_text = re.sub(r'^```\s*', '', json_text)
        json_text = re.sub(r'\s*```$', '', json_text)

        stripped = json_text.lstrip()
        if stripped.startswith('documentInfo') or stripped.startswith('structureAnalysis') or stripped.startswith('coreContent'):
            json_text = '{' + json_text + '}'

        replacements = {
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
        }
        for k, v in replacements.items():
            json_text = json_text.replace(k, v)

        json_text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        json_text = re.sub(r',\s*,', ',', json_text)

        json_text = re.sub(r'([0-9])\s+(})', r'\1\2', json_text)
        json_text = re.sub(r'"keywords"\s*:\s*\[\s*\]', '"keywords": []', json_text)
        json_text = re.sub(r'"classificationTags"\s*:\s*\[\s*\]', '"classificationTags": []', json_text)

        def clean_control_chars(text: str) -> str:
            result = []
            in_string = False
            escape_next = False
            for ch in text:
                if escape_next:
                    result.append(ch)
                    escape_next = False
                    continue
                if ch == "\\":
                    result.append(ch)
                    escape_next = True
                    continue
                if ch == '"':
                    result.append(ch)
                    in_string = not in_string
                    continue
                if in_string and ord(ch) < 32:
                    if ch == '\n':
                        result.append('\\n')
                    elif ch == '\r':
                        result.append('\\r')
                    elif ch == '\t':
                        result.append('\\t')
                    else:
                        result.append(' ')
                else:
                    result.append(ch)
            return ''.join(result)

        json_text = clean_control_chars(json_text)

        json_text = re.sub(
            r'(\})(\s*\"[A-Za-z_][A-Za-z0-9_]*\")',
            r'\1,\2',
            json_text,
        )
        json_text = re.sub(
            r'(\])(\s*\"[A-Za-z_][A-Za-z0-9_]*\")',
            r'\1,\2',
            json_text,
        )

        brace_count = 0
        in_string = False
        escape_next = False
        end_pos = None
        for idx, ch in enumerate(json_text):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\':
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = idx + 1
                        break
        if end_pos is not None:
            json_text = json_text[:end_pos]

        return json_text.strip()

    def _aggressive_json_repair(self, json_text: str) -> str:
        stripped = json_text.lstrip()
        if stripped.startswith('documentInfo') or stripped.startswith('structureAnalysis') or stripped.startswith('coreContent'):
            json_text = '{' + json_text + '}'

        json_text = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_text)
        json_text = re.sub(r"'([^'\\]*(\\.[^'\\]*)*)'", r'"\1"', json_text)
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        json_text = re.sub(r',\s*,', ',', json_text)
        json_text = re.sub(r'//.*$', '', json_text, flags=re.MULTILINE)
        json_text = re.sub(r'/\*.*?\*/', '', json_text, flags=re.DOTALL)

        open_braces = json_text.count('{') - json_text.count('}')
        open_brackets = json_text.count('[') - json_text.count(']')
        if open_braces > 0:
            json_text += '}' * open_braces
        if open_brackets > 0:
            json_text += ']' * open_brackets

        json_text = re.sub(r'\s+', ' ', json_text)
        return json_text.strip()


__all__ = ["LocalFileAnalyzer"]
