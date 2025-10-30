"""
청크 기반 지식 그래프 생성 엔드포인트

기존 knowledge-graph 엔드포인트를 확장하여 문서 분할 분석을 적용합니다.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies import get_db
from services.chunk_analyzer import ChunkAnalyzer
from services.document_parser_service import DocumentParserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chunk-analysis", tags=["chunk-analysis"])


class ChunkKnowledgeGraphRequest(BaseModel):
    file_path: str
    output_directory: Optional[str] = None
    max_chunk_size: int = 50000
    use_llm: bool = True
    extractors: List[str] = ["KeyBERT", "spaCy NER", "LLM"]
    analysis_types: List[str] = ["keywords", "summary", "structure", "knowledge_graph"]
    force_reparse: bool = False
    force_reanalyze: bool = False
    llm_config: Optional[Dict[str, Any]] = None


class ChunkAnalysisResponse(BaseModel):
    success: bool
    total_chunks: int
    total_content_length: int
    processing_time_seconds: float
    output_directory: str
    saved_files: List[Dict[str, str]]
    chunk_summary: List[Dict[str, Any]]
    integrated_keywords_count: int
    analysis_timestamp: str
    error_message: Optional[str] = None


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


@router.post("/knowledge-graph", response_model=ChunkAnalysisResponse)
async def generate_chunk_knowledge_graph(
    request: ChunkKnowledgeGraphRequest,
    db: Session = Depends(get_db)
):
    """청크 기반 지식 그래프 생성"""

    file_path = _ensure_absolute(Path(request.file_path))
    _validate_file(file_path)

    logger.info(f"🚀 청크 기반 지식 그래프 생성 시작: {file_path}")

    try:
        # 출력 디렉토리 설정
        if request.output_directory:
            output_dir = _ensure_absolute(Path(request.output_directory))
        else:
            # 기본 출력 디렉토리: 파일 경로 기반
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = file_path.parent / f"chunk_analysis_{file_path.stem}_{timestamp}"

        output_dir.mkdir(parents=True, exist_ok=True)

        # 청크 분석기 초기화 및 실행
        analyzer = ChunkAnalyzer(db)

        start_time = datetime.now()

        integrated_result = analyzer.analyze_document_with_chunking(
            file_path=str(file_path),
            output_directory=str(output_dir),
            max_chunk_size=request.max_chunk_size,
            use_llm=request.use_llm,
            extractors=request.extractors,
            analysis_types=request.analysis_types
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # 저장된 파일 목록 수집
        saved_files = _collect_saved_files(output_dir)

        # 청크 요약 정보 생성
        chunk_summary = []
        for chunk_result in integrated_result.chunk_results:
            chunk_summary.append({
                "chunk_id": chunk_result.chunk_id,
                "level": chunk_result.level,
                "content_length": chunk_result.content_length,
                "keywords_count": len(chunk_result.keywords),
                "has_summary": bool(chunk_result.summary),
                "has_structure_analysis": bool(chunk_result.structure_analysis),
                "has_knowledge_graph": bool(chunk_result.knowledge_graph)
            })

        logger.info(f"✅ 청크 기반 지식 그래프 생성 완료 (소요시간: {processing_time:.2f}초)")

        return ChunkAnalysisResponse(
            success=True,
            total_chunks=integrated_result.total_chunks,
            total_content_length=integrated_result.total_content_length,
            processing_time_seconds=processing_time,
            output_directory=str(output_dir),
            saved_files=saved_files,
            chunk_summary=chunk_summary,
            integrated_keywords_count=len(integrated_result.integrated_keywords),
            analysis_timestamp=end_time.isoformat()
        )

    except Exception as e:
        logger.error(f"❌ 청크 기반 지식 그래프 생성 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"청크 분석 실패: {str(e)}"
        )


@router.get("/knowledge-graph", response_model=ChunkAnalysisResponse)
async def get_chunk_knowledge_graph(
    file_path: str = Query(..., description="분석할 파일 경로"),
    output_directory: Optional[str] = Query(None, description="출력 디렉토리"),
    max_chunk_size: int = Query(50000, description="최대 청크 크기"),
    use_llm: bool = Query(True, description="LLM 사용 여부"),
    extractors: str = Query("KeyBERT,spaCy NER,LLM", description="추출기 목록 (콤마 구분)"),
    analysis_types: str = Query("keywords,summary,structure,knowledge_graph", description="분석 유형 (콤마 구분)"),
    force_reparse: bool = Query(False, description="강제 재파싱"),
    force_reanalyze: bool = Query(False, description="강제 재분석"),
    db: Session = Depends(get_db)
):
    """GET 방식으로 청크 기반 지식 그래프 생성"""

    # 문자열 파라미터를 리스트로 변환
    extractors_list = [ext.strip() for ext in extractors.split(",")]
    analysis_types_list = [analysis_type.strip() for analysis_type in analysis_types.split(",")]

    request = ChunkKnowledgeGraphRequest(
        file_path=file_path,
        output_directory=output_directory,
        max_chunk_size=max_chunk_size,
        use_llm=use_llm,
        extractors=extractors_list,
        analysis_types=analysis_types_list,
        force_reparse=force_reparse,
        force_reanalyze=force_reanalyze
    )

    return await generate_chunk_knowledge_graph(request, db)


@router.get("/chunk-status/{chunk_id}")
async def get_chunk_status(
    chunk_id: str,
    output_directory: str = Query(..., description="분석 결과 디렉토리"),
    db: Session = Depends(get_db)
):
    """특정 청크의 분석 상태 조회"""

    try:
        output_path = Path(output_directory)

        if not output_path.exists():
            raise HTTPException(status_code=404, detail="출력 디렉토리를 찾을 수 없습니다")

        # 청크 분석기 초기화 (상태 조회용)
        analyzer = ChunkAnalyzer(db)
        analyzer.prompt_manager = analyzer.ChunkPromptManager(str(output_path))

        # 청크 프롬프트 요약 조회
        chunk_summary = analyzer.prompt_manager.get_chunk_prompt_summary(chunk_id)

        return {
            "chunk_id": chunk_id,
            "status": "completed" if chunk_summary["total_executions"] > 0 else "pending",
            **chunk_summary
        }

    except Exception as e:
        logger.error(f"❌ 청크 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"청크 상태 조회 실패: {str(e)}")


@router.get("/analysis-report")
async def get_analysis_report(
    output_directory: str = Query(..., description="분석 결과 디렉토리"),
    format: str = Query("json", description="보고서 형식 (json/markdown)")
):
    """전체 분석 보고서 조회"""

    try:
        output_path = Path(output_directory)

        if not output_path.exists():
            raise HTTPException(status_code=404, detail="출력 디렉토리를 찾을 수 없습니다")

        # 통합 분석 결과 파일 조회
        integrated_result_file = output_path / "integrated_analysis_result.json"
        if not integrated_result_file.exists():
            raise HTTPException(status_code=404, detail="통합 분석 결과를 찾을 수 없습니다")

        with open(integrated_result_file, 'r', encoding='utf-8') as f:
            integrated_data = json.load(f)

        if format.lower() == "markdown":
            # 마크다운 형식 보고서 생성
            report_lines = [
                f"# 문서 분석 보고서",
                f"생성일시: {datetime.now().isoformat()}",
                f"",
                f"## 분석 개요",
                f"- 총 청크 수: {integrated_data.get('total_chunks', 0)}",
                f"- 총 콘텐츠 길이: {integrated_data.get('total_content_length', 0):,}자",
                f"- 통합 키워드 수: {len(integrated_data.get('integrated_keywords', []))}",
                f"",
                f"## 계층적 요약",
                f"```json",
                json.dumps(integrated_data.get('hierarchical_summary', {}), ensure_ascii=False, indent=2),
                f"```",
                f"",
                f"## 상위 키워드",
            ]

            for i, keyword in enumerate(integrated_data.get('integrated_keywords', [])[:10], 1):
                keyword_text = keyword.get('keyword', '알 수 없음')
                frequency = keyword.get('frequency', 1)
                sources = len(keyword.get('sources', []))
                report_lines.append(f"{i}. **{keyword_text}** (빈도: {frequency}, 출처: {sources}개 청크)")

            return {
                "format": "markdown",
                "content": "\n".join(report_lines)
            }

        else:
            # JSON 형식 반환
            return {
                "format": "json",
                "content": integrated_data
            }

    except Exception as e:
        logger.error(f"❌ 분석 보고서 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 보고서 조회 실패: {str(e)}")


def _collect_saved_files(output_dir: Path) -> List[Dict[str, str]]:
    """출력 디렉토리에서 저장된 파일 목록 수집"""

    saved_files = []

    # 주요 결과 파일들
    main_files = {
        "integrated_analysis_result.json": "통합 분석 결과",
        "chunks_detailed_results.json": "청크별 상세 결과",
        "chunks_info.json": "청크 정보",
        "document_structure.json": "문서 구조"
    }

    for filename, description in main_files.items():
        file_path = output_dir / filename
        if file_path.exists():
            saved_files.append({
                "type": "main_result",
                "path": str(file_path),
                "description": description,
                "size": str(file_path.stat().st_size)
            })

    # 청크 텍스트 파일들
    chunks_text_dir = output_dir / "chunks_text"
    if chunks_text_dir.exists():
        for chunk_file in chunks_text_dir.glob("*.txt"):
            saved_files.append({
                "type": "chunk_text",
                "path": str(chunk_file),
                "description": f"청크 텍스트: {chunk_file.stem}",
                "size": str(chunk_file.stat().st_size)
            })

    # 프롬프트 파일들
    prompts_dir = output_dir / "chunk_prompts"
    if prompts_dir.exists():
        for prompt_file in prompts_dir.glob("*.txt"):
            saved_files.append({
                "type": "prompt",
                "path": str(prompt_file),
                "description": f"프롬프트: {prompt_file.stem}",
                "size": str(prompt_file.stat().st_size)
            })

    # 결과 파일들
    results_dir = output_dir / "chunk_results"
    if results_dir.exists():
        for result_file in results_dir.glob("*"):
            if result_file.is_file():
                saved_files.append({
                    "type": "chunk_result",
                    "path": str(result_file),
                    "description": f"청크 결과: {result_file.stem}",
                    "size": str(result_file.stat().st_size)
                })

    return saved_files


__all__ = ["router"]