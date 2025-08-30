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
    base_dir: str = "tests/debug_outputs/llm",
) -> Dict[str, Any]:
    """
    Persist LLM I/O to files and optionally log a concise summary.

    - Creates folder: {base_dir}/{YYYYMMDD}/{HHMMSS}_{label}_{uuid}/
    - Writes: prompt.txt, response.txt, meta.json

    Returns a dict with paths and basic stats for further logging if needed.
    """
    ts = datetime.now()
    day_dir = Path(base_dir) / ts.strftime("%Y%m%d")
    session_dir = day_dir / f"{ts.strftime('%H%M%S')}_{label}_{_short_uuid()}"
    _ensure_dir(session_dir)

    # Save prompt and response
    prompt_file = session_dir / "prompt.txt"
    response_file = session_dir / "response.txt"
    meta_file = session_dir / "meta.json"

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

    # Standard logger output (concise)
    if logger is not None:
        try:
            logger.info(
                "📝 LLM I/O 저장 - label=%s provider=%s model=%s prompt=%d자 response=%d자 path=%s",
                label,
                provider,
                model,
                info["prompt_chars"],
                info["response_chars"],
                str(session_dir),
            )
        except Exception:
            pass

    return {
        "dir": str(session_dir),
        "prompt_file": str(prompt_file),
        "response_file": str(response_file),
        "meta_file": str(meta_file),
        **info,
    }

