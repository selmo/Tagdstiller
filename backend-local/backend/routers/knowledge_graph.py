"""LLM 구조 분석 전용 엔드포인트 (Knowledge Graph 생성 제외)."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies import get_db
from services.document_parser_service import DocumentParserService
from services.local_file_analyzer import LocalFileAnalyzer
from routers.local_analysis import (
    _collect_saved_files,
    _move_markdown_files_to_correct_location,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local-analysis", tags=["local-analysis"])


class StructureAnalysisRequest(BaseModel):
    file_path: str
    directory: Optional[str] = None
    force_reparse: bool = False
    force_reanalyze: bool = False
    force_rebuild: bool = False
    llm: Optional[Dict[str, Any]] = None


def _ensure_absolute(path: Path) -> Path:
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _validate_file(file_path: Path) -> None:
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
    if file_path.is_dir():
        raise HTTPException(status_code=400, detail="디렉토리가 아닌 파일이어야 합니다")
    if file_path.stat().st_size == 0:
        raise HTTPException(status_code=400, detail="파일이 비어있습니다")
    supported_extensions = {".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".xml", ".hwp"}
    if file_path.suffix.lower() not in supported_extensions:
        raise HTTPException(status_code=400, detail=f"지원되지 않는 파일 형식입니다: {file_path.suffix}")


@router.post("/knowledge-graph")
async def generate_knowledge_graph(req: StructureAnalysisRequest, db: Session = Depends(get_db)):
    file_path = _ensure_absolute(Path(req.file_path))
    _validate_file(file_path)

    directory_path = None
    if req.directory:
        directory_path = _ensure_absolute(Path(req.directory))
        directory_path.mkdir(parents=True, exist_ok=True)

    parser_service = DocumentParserService()
    analyzer = LocalFileAnalyzer(db, initialize_extractors=False)

    output_dir = parser_service.get_output_directory(file_path, directory_path)
    response_path = output_dir / "llm_structure_response.json"

    if not any([req.force_reparse, req.force_reanalyze, req.force_rebuild]) and response_path.exists():
        with response_path.open('r', encoding='utf-8') as f:
            return json.load(f)

    # 1. 파싱 수행 (항상 최고 품질 파서를 사용)
    try:
        if req.force_reparse or not parser_service.has_parsing_results(file_path, directory_path):
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path,
                force_reparse=req.force_reparse,
                directory=directory_path,
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path, directory_path)
    except Exception as parsing_error:
        logger.error("❌ 문서 파싱 실패", exc_info=True)
        raise HTTPException(status_code=500, detail=f"문서 파싱 실패: {parsing_error}")

    if parsing_results.get("parsing_results"):
        _move_markdown_files_to_correct_location(parsing_results, file_path, output_dir)

    # 2. LLM 기반 구조 분석 (기존 결과 재사용 가능)
    structure_result_path = output_dir / "llm_structure_analysis.json"
    llm_overrides = req.llm.copy() if req.llm else {}
    llm_overrides.setdefault("enabled", True)

    if req.force_reanalyze or req.force_rebuild or not structure_result_path.exists():
        best_parser = parsing_results.get("summary", {}).get("best_parser")
        document_text = ""
        if best_parser and best_parser in parsing_results.get("parsing_results", {}):
            parser_dir = parser_service.get_output_directory(file_path, directory_path) / best_parser
            text_file = parser_dir / f"{best_parser}_text.txt"
            if text_file.exists():
                document_text = text_file.read_text(encoding='utf-8')

        structure_results = analyzer.analyze_document_structure_with_llm(
            text=document_text,
            file_path=str(file_path),
            file_extension=file_path.suffix.lower(),
            overrides=llm_overrides,
        )

        structure_results["file_info"] = parsing_results["file_info"]
        structure_results["analysis_timestamp"] = datetime.now().isoformat()
        structure_results["source_parser"] = best_parser

        with structure_result_path.open('w', encoding='utf-8') as f:
            json.dump(structure_results, f, ensure_ascii=False, indent=2)
    else:
        with structure_result_path.open('r', encoding='utf-8') as f:
            structure_results = json.load(f)

    llm_analysis = structure_results.get("llm_analysis")
    if not llm_analysis or not llm_analysis.get("structureAnalysis"):
        raise HTTPException(status_code=500, detail="LLM 구조 분석 결과가 비어있습니다")

    # 3. 결과 저장 및 응답 구성
    output_dir.mkdir(exist_ok=True)

    best_parser = parsing_results.get("summary", {}).get("best_parser")

    saved_files = _collect_saved_files(output_dir, parsing_results)
    if structure_result_path.exists():
        saved_files.insert(0, {
            "type": "structure_analysis",
            "path": str(structure_result_path),
            "description": "LLM 기반 문서 구조 분석 결과",
        })

    api_response = {
        "saved_files": saved_files,
        "output_directory": str(output_dir),
        "generation_timestamp": datetime.now().isoformat(),
        "source_parser": best_parser,
        "llm_analysis": llm_analysis,
        "statistics": {
            "total_saved_files": len(saved_files),
            "file_types": {},
        },
    }

    for file_info in saved_files:
        file_type = file_info.get("type", "unknown")
        api_response["statistics"]["file_types"][file_type] = api_response["statistics"]["file_types"].get(file_type, 0) + 1

    with response_path.open('w', encoding='utf-8') as f:
        json.dump(api_response, f, ensure_ascii=False, indent=2)

    return api_response


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    file_path: str,
    directory: Optional[str] = None,
    force_reparse: bool = False,
    force_reanalyze: bool = False,
    force_rebuild: bool = False,
    db: Session = Depends(get_db),
):
    request = StructureAnalysisRequest(
        file_path=file_path,
        directory=directory,
        force_reparse=force_reparse,
        force_reanalyze=force_reanalyze,
        force_rebuild=force_rebuild,
    )
    return await generate_knowledge_graph(request, db)
