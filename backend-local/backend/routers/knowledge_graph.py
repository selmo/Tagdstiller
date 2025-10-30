"""Knowledge Graph 생성 엔드포인트 - 청크 기반 분석 통합."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies import get_db
from services.document_parser_service import DocumentParserService
from services.local_file_analyzer import LocalFileAnalyzer
from services.chunk_analyzer import ChunkAnalyzer
from services.image_analyzer import ImageAnalyzer
from services.knowledge_graph_builder import KnowledgeGraphBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/local-analysis", tags=["local-analysis"])


class StructureAnalysisRequest(BaseModel):
    file_path: str
    directory: Optional[str] = None
    force_reparse: bool = False
    force_reanalyze: bool = False
    force_rebuild: bool = False
    llm: Optional[Dict[str, Any]] = None

    # 청크 기반 분석 옵션 추가
    use_chunking: bool = False  # 청킹 사용 여부 (기본값: False, 명시적으로 활성화 필요)
    chunk_threshold: int = 30000  # 청킹 문자 수 임계값 (기본 30,000자)
    max_chunk_size: int = 50000
    extractors: List[str] = ["KeyBERT", "spaCy NER", "LLM"]
    analysis_types: List[str] = ["keywords", "summary", "structure", "knowledge_graph"]

    # 이미지 분석 옵션 추가
    analyze_images: bool = False
    extract_images: bool = True

    # 다단계 대화 옵션 추가 (토큰 제한 회피)
    use_multistep: bool = False  # 다단계 대화 방식 사용 여부


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
    analyzer = LocalFileAnalyzer(db)

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

    # 2. 문서 크기 확인 및 청킹 결정
    best_parser = parsing_results.get("summary", {}).get("best_parser")
    document_text = ""
    if best_parser and best_parser in parsing_results.get("parsing_results", {}):
        parser_dir = parser_service.get_output_directory(file_path, directory_path) / best_parser
        text_file = parser_dir / f"{best_parser}_text.txt"
        if text_file.exists():
            document_text = text_file.read_text(encoding='utf-8')

    # 3. 스캔 문서 감지 및 OCR 처리
    document_size = len(document_text)
    min_text_threshold = 500  # 최소 텍스트 길이 임계값

    # 스캔된 문서인지 감지 (텍스트가 너무 적으면 이미지 기반 문서로 판단)
    is_scanned_document = document_size < min_text_threshold and file_path.suffix.lower() == ".pdf"

    if is_scanned_document and req.analyze_images:
        logger.info(f"📸 스캔 문서 감지 (텍스트 {document_size}자 < {min_text_threshold}자), OCR 처리 시작: {file_path}")

        try:
            image_analyzer = ImageAnalyzer(db)
            ocr_result = image_analyzer.extract_full_text_from_scanned_pdf(file_path, output_dir)

            if ocr_result.get("success") and ocr_result.get("extracted_text"):
                # OCR로 추출한 텍스트를 기존 텍스트와 결합
                ocr_text = ocr_result["extracted_text"]
                document_text = f"{document_text}\n\n=== OCR 추출 텍스트 ===\n{ocr_text}"
                document_size = len(document_text)

                logger.info(f"✅ OCR 성공: {ocr_result['pages_processed']}/{ocr_result['total_pages']}페이지, {ocr_result['text_length']}자 추출")
                logger.info(f"📊 총 텍스트 크기: {document_size:,}자 (기존 + OCR 결합)")

                # OCR 결과를 파싱 결과에 추가
                if "ocr_results" not in parsing_results:
                    parsing_results["ocr_results"] = {}
                parsing_results["ocr_results"]["full_document_ocr"] = ocr_result

            else:
                logger.warning(f"⚠️ OCR 실패 또는 텍스트 없음: {ocr_result.get('error', '알 수 없는 오류')}")

        except Exception as ocr_error:
            logger.error(f"❌ OCR 처리 중 오류: {ocr_error}", exc_info=True)
            # OCR 실패해도 기존 텍스트로 계속 진행

    # 청킹 사용 여부 결정 (명시적 요청 시에만)
    if req.use_chunking:
        if document_size > req.chunk_threshold:
            logger.info(f"🧩 청크 기반 분석 모드 (문서 크기: {document_size:,}자 > 임계값: {req.chunk_threshold:,}자)")
            return await _generate_chunk_based_knowledge_graph(req, db, file_path, directory_path)
        else:
            logger.info(f"ℹ️ 청킹 요청되었으나 문서가 작아 전체 분석 진행 (크기: {document_size:,}자 ≤ 임계값: {req.chunk_threshold:,}자)")

    # 기존 방식: 전체 문서 분석
    logger.info(f"📄 전체 문서 분석 모드로 지식 그래프 생성 (문서 크기: {document_size:,}자)")

    # 2. LLM 기반 구조 분석 (기존 결과 재사용 가능)
    structure_result_path = output_dir / "llm_structure_analysis.json"
    llm_overrides = req.llm.copy() if req.llm else {}
    llm_overrides.setdefault("enabled", True)

    if req.force_reanalyze or req.force_rebuild or not structure_result_path.exists():
        structure_results = analyzer.analyze_document_structure_with_llm(
            text=document_text,
            file_path=str(file_path),
            file_extension=file_path.suffix.lower(),
            overrides=llm_overrides,
            use_multistep=req.use_multistep,  # 다단계 대화 옵션 전달
        )

        structure_results["file_info"] = parsing_results["file_info"]
        structure_results["analysis_timestamp"] = datetime.now().isoformat()
        structure_results["source_parser"] = best_parser

        with structure_result_path.open('w', encoding='utf-8') as f:
            json.dump(structure_results, f, ensure_ascii=False, indent=2)
    else:
        with structure_result_path.open('r', encoding='utf-8') as f:
            structure_results = json.load(f)

    if not structure_results.get("llm_success"):
        raise HTTPException(
            status_code=502,
            detail={
                "message": structure_results.get("llm_error", "LLM 구조 분석 실패"),
                "raw_response": structure_results.get("llm_raw_response", ""),
                "analysis_file": str(structure_result_path),
            },
        )

    llm_analysis = structure_results.get("llm_analysis")
    if not llm_analysis or not llm_analysis.get("structureAnalysis"):
        raise HTTPException(
            status_code=502,
            detail={
                "message": "LLM 구조 분석 결과가 비어 있습니다",
                "analysis_file": str(structure_result_path),
            },
        )

    # 3. 이미지 분석 (PDF 파일인 경우, 옵션 활성화 시)
    image_analysis_result = None
    if file_path.suffix.lower() == ".pdf" and (req.analyze_images or req.extract_images):
        image_analyzer = ImageAnalyzer(db)

        if req.analyze_images:
            logger.info(f"🖼️ PDF 이미지 분석 시작: {file_path}")
            # LLM 설정 전달
            llm_config = req.llm.copy() if req.llm else {}

            # 이미지 필터링 설정 추가
            filter_config = {
                "min_width": 150,       # 최소 너비 (작은 로고/아이콘 제외)
                "min_height": 150,      # 최소 높이
                "skip_duplicates": True # 중복 이미지 스킵 (같은 크기 = 로고일 가능성 높음)
            }

            image_analysis_result = image_analyzer.analyze_document_with_images(
                file_path=file_path,
                text_content=document_text,
                output_dir=output_dir,
                llm_config=llm_config,
                filter_config=filter_config
            )
            logger.info(f"✅ 이미지 분석 완료: {image_analysis_result.get('images_count', 0)}개 추출, "
                       f"{image_analysis_result.get('successful_analyses', 0)}개 분석 성공")
        elif req.extract_images:
            # 이미지 추출만 (분석 없음)
            logger.info(f"📸 PDF 이미지 추출 시작: {file_path}")
            images_info = image_analyzer.extract_images_from_pdf(
                file_path=file_path,
                output_dir=output_dir / "images"
            )
            image_analysis_result = {
                "success": True,
                "images_count": len(images_info),
                "extraction_only": True,
                "images_info": images_info
            }

    # 3. 결과 저장 및 응답 구성
    output_dir.mkdir(exist_ok=True)

    best_parser = parsing_results.get("summary", {}).get("best_parser")

    saved_files = []
    if structure_result_path.exists():
        saved_files.append({
            "type": "structure_analysis",
            "path": str(structure_result_path),
            "description": "LLM 기반 문서 구조 분석 결과",
        })

    parsing_result_path = parser_service.get_parsing_result_path(file_path, directory_path)
    if parsing_result_path.exists():
        saved_files.append({
            "type": "parsing_summary",
            "path": str(parsing_result_path),
            "description": "파싱 결과 종합",
        })

    if parsing_results.get("parsing_results"):
        for parser_name, parser_result in parsing_results["parsing_results"].items():
            if not parser_result.get("success"):
                continue
            parser_dir = output_dir / parser_name
            text_file = parser_dir / f"{parser_name}_text.txt"
            if text_file.exists():
                saved_files.append({
                    "type": "extracted_text",
                    "parser": parser_name,
                    "path": str(text_file),
                    "description": f"{parser_name} 파서로 추출된 텍스트",
                })
            metadata_file = parser_dir / f"{parser_name}_metadata.json"
            if metadata_file.exists():
                saved_files.append({
                    "type": "metadata",
                    "parser": parser_name,
                    "path": str(metadata_file),
                    "description": f"{parser_name} 파서 메타데이터",
                })
            structure_file = parser_dir / f"{parser_name}_structure.json"
            if structure_file.exists():
                saved_files.append({
                    "type": "parser_structure",
                    "parser": parser_name,
                    "path": str(structure_file),
                    "description": f"{parser_name} 파서 구조 정보",
                })

    # 이미지 분석 결과 파일 추가
    if image_analysis_result and image_analysis_result.get("success"):
        # 이미지 분석 결과 JSON 파일
        image_result_file = output_dir / "image_analysis.json"
        if image_result_file.exists():
            saved_files.append({
                "type": "image_analysis",
                "path": str(image_result_file),
                "description": f"이미지 분석 결과 ({image_analysis_result.get('images_count', 0)}개 이미지)",
            })

        # 추출된 이미지 파일들
        images_dir = output_dir / "images"
        if images_dir.exists() and any(images_dir.glob("*.png")):
            image_files = list(images_dir.glob("*.png"))
            saved_files.append({
                "type": "extracted_images",
                "path": str(images_dir),
                "description": f"추출된 이미지 파일들 ({len(image_files)}개)",
                "count": len(image_files)
            })

    api_response = {
        "saved_files": saved_files,
        "output_directory": str(output_dir),
        "generation_timestamp": datetime.now().isoformat(),
        "source_parser": best_parser,
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


async def _generate_chunk_based_knowledge_graph(
    req: StructureAnalysisRequest,
    db: Session,
    file_path: Path,
    directory_path: Optional[Path]
):
    """청크 기반 지식 그래프 생성"""

    try:
        # 출력 디렉토리 설정
        if directory_path:
            output_dir = directory_path
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = file_path.parent / f"chunk_kg_{file_path.stem}_{timestamp}"

        output_dir.mkdir(parents=True, exist_ok=True)

        # 청크 분석기 초기화
        chunk_analyzer = ChunkAnalyzer(db)

        # 청크 기반 분석 실행
        start_time = datetime.now()

        integrated_result = chunk_analyzer.analyze_document_with_chunking(
            file_path=str(file_path),
            output_directory=str(output_dir),
            max_chunk_size=req.max_chunk_size,
            use_llm=req.llm is not None and req.llm.get("enabled", True),
            extractors=req.extractors,
            analysis_types=req.analysis_types
        )

        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # 응답 데이터 구성
        chunk_files = []

        # 주요 결과 파일들
        main_files = [
            ("integrated_analysis_result.json", "통합 분석 결과"),
            ("chunks_detailed_results.json", "청크별 상세 결과"),
            ("chunks_info.json", "청크 정보"),
            ("document_structure.json", "문서 구조")
        ]

        for filename, description in main_files:
            file_path_obj = output_dir / filename
            if file_path_obj.exists():
                chunk_files.append({
                    "type": "analysis_result",
                    "path": str(file_path_obj),
                    "description": description
                })

        # 청크별 파일들
        chunks_text_dir = output_dir / "chunks_text"
        if chunks_text_dir.exists():
            for chunk_file in chunks_text_dir.glob("*.txt"):
                chunk_files.append({
                    "type": "chunk_text",
                    "path": str(chunk_file),
                    "description": f"청크 텍스트: {chunk_file.stem}"
                })

        # 프롬프트 파일들
        prompts_dir = output_dir / "chunk_prompts"
        if prompts_dir.exists():
            prompt_count = len(list(prompts_dir.glob("*.txt")))
            chunk_files.append({
                "type": "prompts_directory",
                "path": str(prompts_dir),
                "description": f"생성된 프롬프트 ({prompt_count}개)"
            })

        # 실행 결과 파일들
        results_dir = output_dir / "chunk_results"
        if results_dir.exists():
            result_count = len(list(results_dir.glob("*")))
            chunk_files.append({
                "type": "results_directory",
                "path": str(results_dir),
                "description": f"실행 결과 ({result_count}개)"
            })

        response_data = {
            "analysis_method": "chunk_based_knowledge_graph",
            "success": True,
            "chunks_analyzed": integrated_result.total_chunks,
            "total_content_length": integrated_result.total_content_length,
            "processing_time_seconds": processing_time,
            "integrated_keywords_count": len(integrated_result.integrated_keywords),
            "saved_files": chunk_files,
            "output_directory": str(output_dir),
            "generation_timestamp": end_time.isoformat(),
            "chunk_summary": [
                {
                    "chunk_id": chunk_result.chunk_id,
                    "level": chunk_result.level,
                    "content_length": chunk_result.content_length,
                    "keywords_count": len(chunk_result.keywords),
                    "has_knowledge_graph": bool(chunk_result.knowledge_graph)
                }
                for chunk_result in integrated_result.chunk_results
            ],
            "statistics": {
                "total_saved_files": len(chunk_files),
                "file_types": {},
            }
        }

        # 파일 타입별 통계
        for file_info in chunk_files:
            file_type = file_info.get("type", "unknown")
            response_data["statistics"]["file_types"][file_type] = response_data["statistics"]["file_types"].get(file_type, 0) + 1

        # 응답 저장
        response_path = output_dir / "chunk_knowledge_graph_response.json"
        with response_path.open('w', encoding='utf-8') as f:
            json.dump(response_data, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 청크 기반 지식 그래프 생성 완료 (소요시간: {processing_time:.2f}초)")

        return response_data

    except Exception as e:
        logger.error(f"❌ 청크 기반 지식 그래프 생성 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"청크 기반 분석 실패: {str(e)}")


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    file_path: str,
    directory: Optional[str] = None,
    force_reparse: bool = False,
    force_reanalyze: bool = False,
    force_rebuild: bool = False,
    use_chunking: bool = Query(False, description="청크 기반 분석 사용 여부"),
    max_chunk_size: int = Query(50000, description="최대 청크 크기"),
    extractors: str = Query("KeyBERT,spaCy NER,LLM", description="추출기 목록 (콤마 구분)"),
    analysis_types: str = Query("keywords,summary,structure,knowledge_graph", description="분석 유형 (콤마 구분)"),
    analyze_images: bool = Query(False, description="이미지 분석 활성화 (멀티모달 LLM 사용)"),
    extract_images: bool = Query(True, description="이미지 추출 활성화"),
    db: Session = Depends(get_db),
):
    """GET 방식으로 지식 그래프 생성 (청크 기반 분석 지원)"""

    # 문자열 파라미터를 리스트로 변환
    extractors_list = [ext.strip() for ext in extractors.split(",")]
    analysis_types_list = [analysis_type.strip() for analysis_type in analysis_types.split(",")]

    request = StructureAnalysisRequest(
        file_path=file_path,
        directory=directory,
        force_reparse=force_reparse,
        force_reanalyze=force_reanalyze,
        force_rebuild=force_rebuild,
        use_chunking=use_chunking,
        max_chunk_size=max_chunk_size,
        extractors=extractors_list,
        analysis_types=analysis_types_list,
        analyze_images=analyze_images,
        extract_images=extract_images
    )
    return await generate_knowledge_graph(request, db)


# ============================================================================
# Full Knowledge Graph API - 문서 전체를 Knowledge Graph로 변환
# ============================================================================


class FullKnowledgeGraphRequest(BaseModel):
    """전체 Knowledge Graph 생성 요청"""
    file_path: str
    directory: Optional[str] = None
    domain: str = "general"  # general, technical, academic, business, legal
    force_reparse: bool = False
    include_structure: bool = True  # 구조 분석 정보 포함 여부
    save_format: str = "json"  # json, cypher, graphml, all
    llm: Optional[Dict[str, Any]] = None


@router.post("/full-knowledge-graph")
async def generate_full_knowledge_graph(req: FullKnowledgeGraphRequest, db: Session = Depends(get_db)):
    """
    문서 전체를 Knowledge Graph로 변환하는 전용 API

    메타정보가 아닌 문서 내용 전체를 엔티티와 관계로 추출하여 그래프 구조로 변환합니다.

    Features:
    - 도메인별 맞춤 엔티티/관계 추출 (general, technical, academic, business, legal)
    - 다양한 출력 형식 지원 (JSON, Cypher, GraphML)
    - 구조 정보 통합 분석 (선택)
    - LLM 기반 지능형 추출

    Args:
        req: Knowledge Graph 생성 요청
        db: 데이터베이스 세션

    Returns:
        Knowledge Graph 결과 (nodes, edges, stats, metadata)
    """
    try:
        file_path = _ensure_absolute(Path(req.file_path))
        _validate_file(file_path)

        directory_path = None
        if req.directory:
            directory_path = _ensure_absolute(Path(req.directory))
            directory_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"🔍 Full Knowledge Graph 생성 시작: {file_path.name} (도메인: {req.domain})")

        # 1. 문서 파싱
        parser_service = DocumentParserService()
        output_dir = parser_service.get_output_directory(file_path, directory_path)

        parsing_results = None
        if req.force_reparse or not parser_service.has_parsing_results(file_path, directory_path):
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path,
                force_reparse=req.force_reparse,
                directory=directory_path,
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path, directory_path)

        # 2. 최상의 파서 결과에서 텍스트 추출
        best_parser = parsing_results.get("summary", {}).get("best_parser")
        document_text = ""
        if best_parser and best_parser in parsing_results.get("parsing_results", {}):
            parser_dir = output_dir / best_parser
            text_file = parser_dir / f"{best_parser}_text.txt"
            if text_file.exists():
                document_text = text_file.read_text(encoding='utf-8')
            else:
                raise HTTPException(status_code=500, detail=f"파싱된 텍스트 파일을 찾을 수 없습니다: {text_file}")
        else:
            raise HTTPException(status_code=500, detail="문서 파싱 결과를 찾을 수 없습니다")

        if not document_text or len(document_text) < 100:
            raise HTTPException(status_code=400, detail="문서 텍스트가 너무 짧거나 비어있습니다")

        logger.info(f"📄 문서 텍스트 추출 완료: {len(document_text):,}자")

        # 3. 구조 정보 추출 (선택)
        structure_info = None
        if req.include_structure:
            structure_response_path = output_dir / "llm_structure_analysis.json"
            if structure_response_path.exists():
                with structure_response_path.open('r', encoding='utf-8') as f:
                    structure_info = json.load(f)
                logger.info("📊 기존 구조 분석 정보 로드 완료")
            else:
                # 구조 분석이 없으면 간단히 실행
                analyzer = LocalFileAnalyzer(db)
                structure_result = analyzer.analyze_document_structure_with_llm(
                    text=document_text[:50000],  # 구조 분석은 앞부분만
                    file_path=str(file_path),
                    file_extension=file_path.suffix,
                    overrides=req.llm or {}
                )
                if structure_result.get("success"):
                    structure_info = structure_result.get("analysis", {})
                    logger.info("📊 구조 분석 실행 완료")

        # 4. Knowledge Graph 생성
        kg_builder = KnowledgeGraphBuilder(db)
        kg_result = kg_builder.build_knowledge_graph(
            text=document_text,
            file_path=str(file_path),
            domain=req.domain,
            structure_info=structure_info,
            llm_config=req.llm or {}
        )

        if not kg_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Knowledge Graph 생성 실패: {kg_result.get('error', '알 수 없는 오류')}"
            )

        # 5. Knowledge Graph 저장
        saved_files = kg_builder.save_knowledge_graph(
            kg_result=kg_result,
            output_dir=output_dir,
            format=req.save_format
        )

        # 6. 최종 응답 구성
        response = {
            "success": True,
            "file_path": str(file_path),
            "domain": req.domain,
            "graph": kg_result.get("graph", {}),
            "stats": kg_result.get("stats", {}),
            "metadata": kg_result.get("metadata", {}),
            "saved_files": saved_files,
            "extraction_date": kg_result.get("extraction_date"),
        }

        logger.info(
            f"✅ Full Knowledge Graph 생성 완료: "
            f"{response['stats'].get('entity_count', 0)}개 엔티티, "
            f"{response['stats'].get('relationship_count', 0)}개 관계"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Full Knowledge Graph 생성 중 오류: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Knowledge Graph 생성 실패: {str(e)}")


@router.get("/full-knowledge-graph")
async def get_full_knowledge_graph(
    file_path: str,
    directory: Optional[str] = None,
    domain: str = Query("general", description="문서 도메인 (general/technical/academic/business/legal)"),
    force_reparse: bool = Query(False, description="강제 재파싱"),
    include_structure: bool = Query(True, description="구조 분석 정보 포함"),
    save_format: str = Query("json", description="저장 형식 (json/cypher/graphml/all)"),
    db: Session = Depends(get_db),
):
    """GET 방식으로 전체 Knowledge Graph 생성"""

    request = FullKnowledgeGraphRequest(
        file_path=file_path,
        directory=directory,
        domain=domain,
        force_reparse=force_reparse,
        include_structure=include_structure,
        save_format=save_format
    )
    return await generate_full_knowledge_graph(request, db)
