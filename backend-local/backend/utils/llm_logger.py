import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _short_uuid() -> str:
    return str(uuid.uuid4())[:8]


def log_prompt_and_response(
    *,
    label: str,
    provider: str,
    model: str,
    prompt: str,
    response: str,
    logger=None,
    meta: Optional[Dict[str, Any]] = None,
    base_dir: str = "llm_logs",
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Persist LLM I/O to files and optionally log a concise summary.

    - Creates folder: {base_dir}/{YYYYMMDD}/{HHMMSS}_{label}_{uuid}/
    - Writes: prompt.txt, response.txt, meta.json, request.json, response.json

    Returns a dict with paths and basic stats for further logging if needed.
    """
    ts = datetime.now()
    day_dir = Path(base_dir) / ts.strftime("%Y%m%d")
    session_dir = day_dir / f"{ts.strftime('%H%M%S')}_{label}_{_short_uuid()}"
    _ensure_dir(session_dir)

    # Save prompt and response (backward compatibility)
    prompt_file = session_dir / "prompt.txt"
    response_file = session_dir / "response.txt"
    meta_file = session_dir / "meta.json"
    
    # New: Save raw JSON request and response
    request_json_file = session_dir / "request.json"
    response_json_file = session_dir / "response.json"
    combined_json_file = session_dir / "llm_interaction.json"

    try:
        with open(prompt_file, "w", encoding="utf-8") as f:
            f.write(prompt or "")
    except Exception:
        # Fallback to ensure the directory exists and continue
        pass

    try:
        with open(response_file, "w", encoding="utf-8") as f:
            f.write(response or "")
    except Exception:
        pass

    # 저장 전 JSON 데이터 확인 디버그 로깅
    if logger:
        logger.info(f"🔍 JSON 데이터 존재 확인 - request_data: {bool(request_data)}, response_data: {bool(response_data)}")
        if request_data:
            logger.info(f"📥 request_data 내용 (타입: {type(request_data)}): {str(request_data)[:100]}...")
        if response_data:
            logger.info(f"📤 response_data 내용 (타입: {type(response_data)}): {str(response_data)[:100]}...")

    # Save raw request data as JSON
    if request_data:
        try:
            with open(request_json_file, "w", encoding="utf-8") as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            if logger:
                logger.warning(f"Failed to save request JSON: {e}")

    # Save raw response data as JSON
    if response_data:
        try:
            with open(response_json_file, "w", encoding="utf-8") as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            if logger:
                logger.warning(f"Failed to save response JSON: {e}")

    # Combined interaction log
    combined_data = {
        "timestamp": ts.isoformat(),
        "label": label,
        "provider": provider,
        "model": model,
        "prompt": prompt or "",
        "response": response or "",
        "prompt_chars": len(prompt or ""),
        "response_chars": len(response or ""),
        "request_data": request_data,
        "response_data": response_data,
        "meta": meta or {}
    }

    try:
        with open(combined_json_file, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        if logger:
            logger.warning(f"Failed to save combined JSON: {e}")

    info = {
        "timestamp": ts.isoformat(),
        "label": label,
        "provider": provider,
        "model": model,
        "prompt_chars": len(prompt or ""),
        "response_chars": len(response or ""),
    }
    if meta:
        info.update({"meta": meta})

    try:
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass

    # Enhanced logger output with JSON info
    if logger is not None:
        try:
            json_info = ""
            if request_data or response_data:
                json_info = f" [JSON저장: request={bool(request_data)}, response={bool(response_data)}]"
            
            logger.info(
                "📝 LLM I/O 저장 - label=%s provider=%s model=%s prompt=%d자 response=%d자 path=%s%s",
                label,
                provider,
                model,
                info["prompt_chars"],
                info["response_chars"],
                str(session_dir),
                json_info,
            )
        except Exception:
            pass

    return {
        "dir": str(session_dir),
        "prompt_file": str(prompt_file),
        "response_file": str(response_file),
        "meta_file": str(meta_file),
        "request_json_file": str(request_json_file) if request_data else None,
        "response_json_file": str(response_json_file) if response_data else None,
        "combined_json_file": str(combined_json_file),
        **info,
    }

