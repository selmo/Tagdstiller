"""LLM-only document structure analyzer for the backend-local service."""

from __future__ import annotations

import json
import logging
import re
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

        truncated_text = text[:15000]
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

        json_response = json.loads(response_text)

        return {
            "analysis_method": "llm_only",
            "llm_success": True,
            "llm_model": model_name,
            "llm_analysis": json_response,
        }

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------
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

        response = requests.post(
            f"{conf.get('base_url', 'https://generativelanguage.googleapis.com')}/v1beta/{conf.get('model', 'models/gemini-1.5-pro')}:streamGenerateContent?key={api_key}",
            json=payload,
            timeout=conf.get("timeout", 120),
            stream=True,
        )
        response.raise_for_status()

        raw_lines: list[str] = []
        sse_payloads: list[str] = []
        chunk_counter = 0
        max_chunks_for_progress = 10
        for line in response.iter_lines(decode_unicode=True):
            if line is None:
                continue
            raw_lines.append(line)
            chunk_counter += 1
            if chunk_counter <= max_chunks_for_progress or chunk_counter % 10 == 0:
                self.logger.info("🔸 Gemini streaming chunk #%d", chunk_counter)
            payload_line = line[5:].strip() if line.startswith("data:") else line.strip()
            if payload_line:
                sse_payloads.append(payload_line)

        raw_text = "\n".join(raw_lines)
        merged_payload = "\n".join(sse_payloads)

        if not merged_payload:
            raise LLMJsonError("Gemini API returned no content", raw_text)

        try:
            parsed = json.loads(merged_payload)
        except json.JSONDecodeError as exc:
            raise LLMJsonError(f"Gemini response JSON parse failure: {exc}", merged_payload) from exc

        entries: list[Dict[str, Any]]
        if isinstance(parsed, dict):
            entries = [parsed]
        elif isinstance(parsed, list):
            entries = [item for item in parsed if isinstance(item, dict)]
        else:
            raise LLMJsonError("Unexpected Gemini response format", merged_payload)

        text_chunks: list[str] = []
        accumulated = []
        for entry in entries:
            for candidate in entry.get("candidates", []):
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if isinstance(part, dict):
                        text_part = part.get("text")
                        if isinstance(text_part, str):
                            text_chunks.append(text_part)
                            accumulated.append(text_part)
                            break

        if not text_chunks:
            raise LLMJsonError("Gemini response contained no text parts", merged_payload)

        merged = "".join(text_chunks).strip()
        self.logger.info("✅ Gemini response merged length: %d characters", len(merged))
        if not merged:
            raise LLMJsonError("Gemini response text is empty", merged_payload)

        return merged, merged_payload

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
