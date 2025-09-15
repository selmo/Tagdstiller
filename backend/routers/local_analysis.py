"""
로컬 파일 분석 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

from dependencies import get_db
from services.local_file_analyzer import LocalFileAnalyzer
from services.document_parser_service import DocumentParserService
from services.memgraph_service import MemgraphService


# Request/Response 모델
class AnalyzeFileRequest(BaseModel):
    file_path: str
    extractors: Optional[List[str]] = None
    force_reanalyze: bool = False
    force_reparse: bool = False  # 파싱부터 다시 수행할지 여부
    directory: Optional[str] = None


class FileAnalysisResponse(BaseModel):
    file_info: Dict[str, Any]
    content_info: Optional[Dict[str, Any]] = None
    extraction_info: Optional[Dict[str, Any]] = None
    keywords: Optional[Dict[str, List[Dict[str, Any]]]] = None
    analysis_status: str
    analysis_timestamp: Optional[str] = None
    result_file: Optional[str] = None
    error_message: Optional[str] = None


class FileStatusResponse(BaseModel):
    file_path: str
    exists: bool
    supported: bool
    has_analysis: bool
    analysis_timestamp: Optional[str] = None
    result_file: Optional[str] = None


class ParseDocumentRequest(BaseModel):
    file_path: str
    force_reparse: bool = False
    directory: Optional[str] = None


class DocumentParsingResponse(BaseModel):
    file_info: Dict[str, Any]
    parsing_timestamp: str
    parsers_used: List[str]
    parsing_results: Dict[str, Any]
    summary: Dict[str, Any]
    output_directory: str
    saved_files: Optional[List[Dict[str, Any]]] = None


# 헬퍼 함수
def _collect_saved_files(output_dir: Path, parsing_results: dict) -> list:
    """저장된 파일들의 정보를 수집합니다."""
    saved_files = []
    
    # 파싱 결과 종합 파일
    parsing_result_path = output_dir / "parsing_results.json"
    if parsing_result_path.exists():
        saved_files.append({
            "type": "parsing_summary",
            "path": str(parsing_result_path),
            "description": "파싱 결과 종합 파일"
        })
    
    # Markdown 파일들
    docling_md = output_dir / "docling.md"
    if docling_md.exists():
        saved_files.append({
            "type": "markdown",
            "parser": "docling",
            "path": str(docling_md),
            "description": "Docling 파서로 생성된 Markdown 파일"
        })
    
    pymupdf_md = output_dir / "pymupdf4llm.md"
    if pymupdf_md.exists():
        saved_files.append({
            "type": "markdown", 
            "parser": "pdf_parser",
            "path": str(pymupdf_md),
            "description": "PyMuPDF4LLM으로 생성된 Markdown 파일"
        })
    
    # 키워드 분석 파일
    keyword_analysis = output_dir / "keyword_analysis.json"
    if keyword_analysis.exists():
        saved_files.append({
            "type": "keyword_analysis",
            "path": str(keyword_analysis),
            "description": "키워드 분석 결과"
        })
    
    # 각 파서별 저장된 파일들
    for parser_name, parser_result in parsing_results.get("parsing_results", {}).items():
        if parser_result.get("success"):
            parser_dir = output_dir / parser_name
            
            # 텍스트 파일
            text_file = parser_dir / f"{parser_name}_text.txt"
            if text_file.exists():
                saved_files.append({
                    "type": "extracted_text",
                    "parser": parser_name,
                    "path": str(text_file),
                    "description": f"{parser_name} 파서로 추출된 텍스트"
                })
            
            # 메타데이터 파일
            metadata_file = parser_dir / f"{parser_name}_metadata.json"
            if metadata_file.exists():
                saved_files.append({
                    "type": "metadata",
                    "parser": parser_name,
                    "path": str(metadata_file),
                    "description": f"{parser_name} 파서 메타데이터"
                })
            
            # 구조 정보 파일
            structure_file = parser_dir / f"{parser_name}_structure.json"
            if structure_file.exists():
                saved_files.append({
                    "type": "parser_structure",
                    "parser": parser_name,
                    "path": str(structure_file),
                    "description": f"{parser_name} 파서 구조 정보"
                })
    
    return saved_files


def _move_markdown_files_to_correct_location(parsing_results, file_path_obj, output_dir):
    """Markdown 파일들을 올바른 위치로 이동하고 원본 위치의 파일들을 정리"""
    import shutil
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Markdown 파일 이동 검사 시작: {output_dir}")
    
    # 원본 파일 디렉토리 (파서가 기본적으로 생성하는 위치)
    original_dir = file_path_obj.parent / file_path_obj.stem
    
    # 먼저 원본 디렉토리의 모든 Markdown 파일을 찾아서 이동
    if original_dir.exists() and original_dir != output_dir:
        logger.info(f"📁 원본 디렉토리 검사: {original_dir}")
        
        # docling.md 파일 처리
        docling_md = original_dir / "docling.md"
        if docling_md.exists():
            target_md = output_dir / "docling.md"
            try:
                target_md.parent.mkdir(parents=True, exist_ok=True)
                if target_md.exists():
                    target_md.unlink()
                shutil.copy2(str(docling_md), str(target_md))
                docling_md.unlink()
                logger.info(f"✅ docling.md 이동 완료: {docling_md} → {target_md}")
                
                # 파싱 결과에서 경로 업데이트
                if "docling" in parsing_results.get("parsing_results", {}):
                    parsing_results["parsing_results"]["docling"]["md_file_path"] = str(target_md)
            except Exception as e:
                logger.warning(f"⚠️ docling.md 이동 실패: {e}")
        
        # pymupdf4llm.md 파일 처리
        pymupdf_md = original_dir / "pymupdf4llm.md"
        if pymupdf_md.exists():
            target_md = output_dir / "pymupdf4llm.md"
            try:
                target_md.parent.mkdir(parents=True, exist_ok=True)
                if target_md.exists():
                    target_md.unlink()
                shutil.copy2(str(pymupdf_md), str(target_md))
                pymupdf_md.unlink()
                logger.info(f"✅ pymupdf4llm.md 이동 완료: {pymupdf_md} → {target_md}")
                
                # 파싱 결과에서 경로 업데이트
                if "pdf_parser" in parsing_results.get("parsing_results", {}):
                    parsing_results["parsing_results"]["pdf_parser"]["md_file_path"] = str(target_md)
            except Exception as e:
                logger.warning(f"⚠️ pymupdf4llm.md 이동 실패: {e}")
        
        # 원본 디렉토리가 비어있으면 삭제
        try:
            if original_dir.exists() and not any(original_dir.iterdir()):
                original_dir.rmdir()
                logger.info(f"🗑️ 빈 원본 디렉토리 삭제: {original_dir}")
        except Exception as e:
            logger.warning(f"⚠️ 원본 디렉토리 삭제 실패: {e}")
    
    # 기존 로직도 유지 (파싱 결과에 있는 md_file_path 처리)
    for parser_name, parser_result in parsing_results.get("parsing_results", {}).items():
        if not parser_result.get("success"):
            continue
            
        md_file_path = parser_result.get("md_file_path")
        
        if not md_file_path:
            continue
            
        source_md_file = Path(md_file_path)
        
        if not source_md_file.exists():
            continue
            
        # 올바른 위치로 이동
        target_md_file = output_dir / source_md_file.name
        
        # 이미 올바른 위치에 있는지 확인
        if source_md_file == target_md_file:
            continue
            
        try:
            # 타겟 디렉토리가 존재하는지 확인
            target_md_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 타겟 파일이 이미 존재하면 덮어쓰기
            if target_md_file.exists():
                target_md_file.unlink()
            
            # 파일 복사 후 원본 강제 삭제
            shutil.copy2(str(source_md_file), str(target_md_file))
            
            # 원본 파일 강제 삭제
            try:
                source_md_file.unlink()
                logger.info(f"📝 Markdown 파일 이동 완료: {source_md_file} → {target_md_file}")
            except Exception as delete_error:
                logger.warning(f"⚠️ 원본 Markdown 파일 삭제 실패: {delete_error}")
            
            # 파싱 결과 업데이트
            parser_result["md_file_path"] = str(target_md_file)
            
        except Exception as move_error:
            logger.warning(f"⚠️ Markdown 파일 이동 실패 ({parser_name}): {move_error}")


router = APIRouter(prefix="/local-analysis", tags=["local-analysis"])


@router.post("/parse", response_model=DocumentParsingResponse)
async def parse_document_comprehensive(
    request: ParseDocumentRequest,
    db: Session = Depends(get_db)
):
    """
    문서를 모든 적용 가능한 파서로 완전 파싱합니다.
    
    - **file_path**: 파싱할 문서 경로
    - **force_reparse**: 기존 결과 무시하고 재파싱 여부 (기본값: false)
    
    항상 모든 파서를 사용하여 최상의 파싱 결과를 제공합니다.
    구조화된 파서(Docling, PyMuPDF4LLM 등)는 구조 정보도 함께 저장합니다.
    """
    from pathlib import Path
    
    parser_service = DocumentParserService()
    
    try:
        file_path = Path(request.file_path)
        
        # 파일 존재 여부 확인
        if not file_path.exists():
            if not file_path.is_absolute():
                # 상대 경로인 경우 현재 작업 디렉토리 기준으로 확인
                file_path = Path.cwd() / file_path
                
        if not file_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {request.file_path}")
        
        # 지원 파일 형식 확인
        if not parser_service.is_supported_file(file_path):
            raise ValueError(f"지원하지 않는 파일 형식입니다: {file_path.suffix}")
        
        # 디렉토리 파라미터 처리
        directory = None
        if request.directory:
            directory = Path(request.directory)
            if not directory.is_absolute():
                directory = Path.cwd() / directory
            directory.mkdir(parents=True, exist_ok=True)
        
        # 완전 파싱 수행
        results = parser_service.parse_document_comprehensive(
            file_path=file_path,
            force_reparse=request.force_reparse,
            directory=directory
        )
        
        # 저장된 파일 경로 수집
        output_dir = parser_service.get_output_directory(file_path, directory)
        saved_files = []
        
        # 파싱 결과 종합 파일
        parsing_result_path = parser_service.get_parsing_result_path(file_path, directory)
        if parsing_result_path.exists():
            saved_files.append({
                "type": "parsing_summary",
                "path": str(parsing_result_path),
                "description": "파싱 결과 종합 파일"
            })
        
        # 각 파서별 저장된 파일들
        for parser_name, parser_result in results["parsing_results"].items():
            if parser_result.get("success"):
                parser_dir = output_dir / parser_name
                
                # 텍스트 파일
                text_file = parser_dir / f"{parser_name}_text.txt"
                if text_file.exists():
                    saved_files.append({
                        "type": "extracted_text",
                        "parser": parser_name,
                        "path": str(text_file),
                        "description": f"{parser_name} 파서로 추출된 텍스트"
                    })
                
                # 메타데이터 파일
                metadata_file = parser_dir / f"{parser_name}_metadata.json"
                if metadata_file.exists():
                    saved_files.append({
                        "type": "metadata",
                        "parser": parser_name,
                        "path": str(metadata_file),
                        "description": f"{parser_name} 파서 메타데이터"
                    })
                
                # 구조 정보 파일
                structure_file = parser_dir / f"{parser_name}_structure.json"
                if structure_file.exists():
                    saved_files.append({
                        "type": "parser_structure",
                        "parser": parser_name,
                        "path": str(structure_file),
                        "description": f"{parser_name} 파서 구조 정보"
                    })
                
                # Docling markdown 파일
                if parser_name == "docling" and parser_result.get("md_file_path"):
                    md_file_path = Path(parser_result["md_file_path"])
                    if md_file_path.exists():
                        saved_files.append({
                            "type": "markdown",
                            "parser": parser_name,
                            "path": str(md_file_path),
                            "description": "Docling 파서로 생성된 Markdown 파일"
                        })
        
        return DocumentParsingResponse(
            file_info=results["file_info"],
            parsing_timestamp=results["parsing_timestamp"],
            parsers_used=results["parsers_used"],
            parsing_results=results["parsing_results"],
            summary=results["summary"],
            output_directory=str(output_dir),
            saved_files=saved_files
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from utils.error_handler import log_and_raise_http_exception, collect_context_info
        
        # 컨텍스트 정보 수집
        context = collect_context_info(locals(), ["file_path", "directory", "force_reparse"])
        
        # 상세한 오류 로깅 및 HTTPException 발생
        log_and_raise_http_exception(
            e, 
            "문서 파싱", 
            context=context,
            logger_name=__name__
        )


@router.get("/parse", response_model=DocumentParsingResponse)
async def parse_document_comprehensive_get(
    file_path: str = Query(..., description="파싱할 문서 경로"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    directory: Optional[str] = Query(None, description="결과 저장 디렉토리"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 문서를 완전 파싱합니다.
    """
    request = ParseDocumentRequest(
        file_path=file_path,
        force_reparse=force_reparse,
        directory=directory
    )
    
    return await parse_document_comprehensive(request, db)


@router.get("/parse/status")
async def get_parsing_status(
    file_path: str = Query(..., description="파싱 상태를 확인할 파일 경로"),
    db: Session = Depends(get_db)
):
    """
    문서의 파싱 상태를 확인합니다.
    """
    from pathlib import Path
    
    parser_service = DocumentParserService()
    
    try:
        file_path_obj = Path(file_path)
        
        # 파일 존재 여부 확인
        if not file_path_obj.exists():
            if not file_path_obj.is_absolute():
                file_path_obj = Path.cwd() / file_path_obj
                
        exists = file_path_obj.exists()
        supported = parser_service.is_supported_file(file_path_obj) if exists else False
        has_parsing = parser_service.has_parsing_results(file_path_obj) if exists and supported else False
        
        result = {
            "file_path": file_path,
            "exists": exists,
            "supported": supported,
            "has_parsing_results": has_parsing,
            "supported_extensions": parser_service.get_supported_extensions()
        }
        
        if has_parsing:
            parsing_results = parser_service.load_existing_parsing_results(file_path_obj)
            if parsing_results:
                result.update({
                    "parsing_timestamp": parsing_results.get("parsing_timestamp"),
                    "parsers_used": parsing_results.get("parsers_used", []),
                    "summary": parsing_results.get("summary", {}),
                    "output_directory": str(parser_service.get_output_directory(file_path_obj))
                })
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상태 확인 중 오류가 발생했습니다: {str(e)}")


@router.get("/parse/results")
async def get_parsing_results(
    file_path: str = Query(..., description="파싱 결과를 조회할 파일 경로"),
    parser_name: Optional[str] = Query(None, description="특정 파서 결과만 조회 (예: docling, pdf_parser)"),
    db: Session = Depends(get_db)
):
    """
    저장된 파싱 결과를 조회합니다.
    """
    from pathlib import Path
    
    parser_service = DocumentParserService()
    
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
            
        if not parser_service.has_parsing_results(file_path_obj):
            raise HTTPException(
                status_code=404, 
                detail=f"파일의 파싱 결과를 찾을 수 없습니다: {file_path}"
            )
        
        results = parser_service.load_existing_parsing_results(file_path_obj)
        
        if parser_name:
            # 특정 파서 결과만 반환
            if parser_name not in results.get("parsing_results", {}):
                raise HTTPException(
                    status_code=404,
                    detail=f"파서 '{parser_name}'의 결과를 찾을 수 없습니다"
                )
            return {
                "file_info": results["file_info"],
                "parsing_timestamp": results["parsing_timestamp"],
                "parser_result": results["parsing_results"][parser_name]
            }
        else:
            # 전체 결과 반환
            return results
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"결과 조회 중 오류가 발생했습니다: {str(e)}")


@router.post("/analyze", response_model=FileAnalysisResponse)
async def analyze_local_file(
    request: AnalyzeFileRequest,
    db: Session = Depends(get_db)
):
    """
    로컬 파일을 분석하여 키워드를 추출합니다.
    
    - **file_path**: 분석할 파일의 경로
    - **extractors**: 사용할 추출기 목록 (기본값: 설정된 기본 추출기)
    - **force_reanalyze**: 기존 분석 결과 무시하고 재분석 여부 (기본값: false)
    - **force_reparse**: 파싱부터 다시 수행할지 여부 (기본값: false)
    
    파싱 결과가 없으면 먼저 완전 파싱을 수행한 후 분석합니다.
    """
    from pathlib import Path
    
    analyzer = LocalFileAnalyzer(db)
    parser_service = DocumentParserService()
    
    try:
        file_path = Path(request.file_path)
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path
            
        # 디렉토리 파라미터 처리
        directory = None
        if request.directory:
            directory = Path(request.directory)
            if not directory.is_absolute():
                directory = Path.cwd() / directory
            directory.mkdir(parents=True, exist_ok=True)
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path, directory) or request.force_reparse:
            # 파싱 결과가 없거나 재파싱 요청시 완전 파싱 수행
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path,
                force_reparse=request.force_reparse,
                directory=directory
            )
        else:
            # 기존 파싱 결과 로드
            parsing_results = parser_service.load_existing_parsing_results(file_path, directory)
        
        # 2. 파싱 결과를 기반으로 키워드 추출 분석 수행
        result = analyzer.analyze_file(
            file_path=str(file_path),
            extractors=request.extractors,
            force_reanalyze=request.force_reanalyze
        )
        
        # 3. 파싱 정보를 결과에 추가
        result["parsing_info"] = {
            "parsing_timestamp": parsing_results.get("parsing_timestamp"),
            "parsers_used": parsing_results.get("parsers_used", []),
            "best_parser": parsing_results.get("summary", {}).get("best_parser"),
            "total_parsers": parsing_results.get("summary", {}).get("total_parsers", 0)
        }
        
        return FileAnalysisResponse(**result)
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from utils.error_handler import log_and_raise_http_exception, collect_context_info
        
        # 컨텍스트 정보 수집
        context = collect_context_info(locals(), ["file_path", "extractors", "force_reanalyze", "force_reparse"])
        
        # 상세한 오류 로깅 및 HTTPException 발생
        log_and_raise_http_exception(
            e, 
            "로컬 파일 분석", 
            context=context,
            logger_name=__name__
        )


@router.get("/analyze", response_model=FileAnalysisResponse)
async def analyze_local_file_get(
    file_path: str = Query(..., description="분석할 파일 경로"),
    extractors: Optional[str] = Query(None, description="사용할 추출기 (쉼표로 구분)"),
    force_reanalyze: bool = Query(False, description="재분석 여부"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    directory: Optional[str] = Query(None, description="결과 저장 디렉토리"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 로컬 파일을 분석합니다.
    """
    extractor_list = None
    if extractors:
        extractor_list = [e.strip() for e in extractors.split(",") if e.strip()]
    
    request = AnalyzeFileRequest(
        file_path=file_path,
        extractors=extractor_list,
        force_reanalyze=force_reanalyze,
        force_reparse=force_reparse,
        directory=directory
    )
    
    return await analyze_local_file(request, db)


@router.get("/status", response_model=FileStatusResponse)
async def get_file_status(
    file_path: str = Query(..., description="확인할 파일 경로"),
    db: Session = Depends(get_db)
):
    """
    파일의 상태를 확인합니다 (존재 여부, 지원 형식 여부, 분석 결과 존재 여부).
    """
    analyzer = LocalFileAnalyzer(db)
    
    exists = analyzer.file_exists(file_path)
    supported = analyzer.is_supported_file(file_path) if exists else False
    
    analysis_timestamp = None
    result_file = None
    has_analysis = False
    
    if exists and supported:
        existing_result = analyzer.load_existing_result(file_path)
        if existing_result:
            has_analysis = True
            analysis_timestamp = existing_result.get("analysis_timestamp")
            result_file = str(analyzer.get_result_file_path(file_path))
    
    return FileStatusResponse(
        file_path=file_path,
        exists=exists,
        supported=supported,
        has_analysis=has_analysis,
        analysis_timestamp=analysis_timestamp,
        result_file=result_file
    )


@router.get("/result", response_model=FileAnalysisResponse)
async def get_analysis_result(
    file_path: str = Query(..., description="결과를 조회할 파일 경로"),
    db: Session = Depends(get_db)
):
    """
    기존 분석 결과를 조회합니다.
    """
    analyzer = LocalFileAnalyzer(db)
    
    existing_result = analyzer.load_existing_result(file_path)
    if not existing_result:
        raise HTTPException(
            status_code=404,
            detail=f"파일의 분석 결과를 찾을 수 없습니다: {file_path}"
        )
    
    return FileAnalysisResponse(**existing_result)


@router.get("/metadata")
async def get_file_metadata(
    file_path: str = Query(..., description="메타데이터를 추출할 파일 경로"),
    force_reparse: bool = Query(False, description="파싱부터 다시 수행할지 여부"),
    parser_name: Optional[str] = Query(None, description="특정 파서의 메타데이터만 조회 (예: docling, pdf_parser)"),
    directory: Optional[str] = Query(None, description="결과를 저장할 디렉토리 경로"),
    use_llm: bool = Query(False, description="LLM 기반 분석 사용 여부"),
    db: Session = Depends(get_db)
):
    """
    파일의 메타데이터를 추출합니다.
    
    - 파싱 결과가 없으면 먼저 완전 파싱을 수행합니다
    - 기본적으로 모든 파서의 메타데이터를 반환합니다
    - parser_name 지정시 해당 파서의 메타데이터만 반환합니다
    
    Dublin Core 표준 메타데이터를 반환합니다.
    """
    from pathlib import Path
    
    parser_service = DocumentParserService()
    
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
            
        # 파일 존재 여부 확인
        if not file_path_obj.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        # 지원 파일 형식 확인
        if not parser_service.is_supported_file(file_path_obj):
            raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다: {file_path}")
        
        # 디렉토리 파라미터 처리
        directory_path = None
        if directory:
            directory_path = Path(directory)
            if not directory_path.is_absolute():
                directory_path = Path.cwd() / directory_path
            directory_path.mkdir(parents=True, exist_ok=True)
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path_obj, directory_path) or force_reparse:
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path_obj,
                force_reparse=force_reparse,
                directory=directory_path
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path_obj, directory_path)
            
        # Markdown 파일들을 올바른 위치로 이동
        if directory_path:
            _move_markdown_files_to_correct_location(parsing_results, file_path_obj, 
                                                    parser_service.get_output_directory(file_path_obj, directory_path))
        
        # 2. 메타데이터 추출
        if parser_name:
            # 특정 파서의 메타데이터만 반환
            if parser_name not in parsing_results.get("parsing_results", {}):
                raise HTTPException(
                    status_code=404,
                    detail=f"파서 '{parser_name}'의 결과를 찾을 수 없습니다"
                )
            parser_result = parsing_results["parsing_results"][parser_name]
            if not parser_result.get("success"):
                raise HTTPException(
                    status_code=400,
                    detail=f"파서 '{parser_name}'의 파싱이 실패했습니다: {parser_result.get('error_message')}"
                )
            # 저장된 파일 경로 수집
            output_dir = parser_service.get_output_directory(file_path_obj, directory_path)
            saved_files = _collect_saved_files(output_dir, parsing_results)
            
            return {
                "file_info": parsing_results["file_info"],
                "parser_name": parser_name,
                "metadata": parser_result.get("metadata"),
                "parsing_timestamp": parsing_results.get("parsing_timestamp"),
                "output_directory": str(output_dir),
                "saved_files": saved_files
            }
        else:
            # 모든 파서의 메타데이터 반환
            all_metadata = {}
            for parser, result in parsing_results.get("parsing_results", {}).items():
                if result.get("success") and result.get("metadata"):
                    all_metadata[parser] = result["metadata"]
            
            # 저장된 파일 경로 수집
            output_dir = parser_service.get_output_directory(file_path_obj, directory_path)
            saved_files = _collect_saved_files(output_dir, parsing_results)
            
            return {
                "file_info": parsing_results["file_info"],
                "parsing_timestamp": parsing_results.get("parsing_timestamp"),
                "parsers_used": parsing_results.get("parsers_used", []),
                "metadata_by_parser": all_metadata,
                "summary": parsing_results.get("summary", {}),
                "output_directory": str(output_dir),
                "saved_files": saved_files
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메타데이터 추출 중 오류가 발생했습니다: {str(e)}")


@router.post("/metadata")
async def extract_file_metadata_post(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    파일의 메타데이터만 추출합니다 (POST 방식).
    """
    file_path = request.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="파일 경로가 필요합니다")
    
    force_reparse = request.get("force_reparse", False)
    parser_name = request.get("parser_name", None)
    directory = request.get("directory", None)
    use_llm = request.get("use_llm", False)
    
    return await get_file_metadata(file_path, force_reparse, parser_name, directory, use_llm, db)


@router.post("/structure-analysis")
async def analyze_document_structure(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    문서의 구조를 분석합니다.
    
    - 파싱 결과가 없으면 먼저 완전 파싱을 수행합니다
    - 문서의 구조적 요소들 (헤더, 단락, 테이블, 이미지 등)을 분석합니다
    - 결과는 파일로 저장되며 기본적으로 재사용됩니다
    """
    from pathlib import Path
    import json
    
    file_path = request.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="파일 경로가 필요합니다")
    
    force_reparse = request.get("force_reparse", False)
    force_reanalyze = request.get("force_reanalyze", False)
    use_llm = request.get("use_llm", True)  # LLM 기반 구조 분석 옵션 (기본값: True)
    directory = request.get("directory")  # 디렉토리 옵션 추가
    
    parser_service = DocumentParserService()
    analyzer = LocalFileAnalyzer(db)
    
    try:
        # 우선 표준화된 절대 경로 해석(현재 작업 디렉토리 기준)
        file_path_obj = analyzer.get_absolute_path(file_path)

        # 파일이 없으면 업로드 루트 기준으로 재시도
        if not file_path_obj.exists():
            try:
                file_root = analyzer.get_file_root()
                candidate = Path(file_root) / file_path if not Path(file_path).is_absolute() else Path(file_path)
                if candidate.exists():
                    file_path_obj = candidate.resolve()
            except Exception:
                pass

        # 최종 존재 여부 확인
        if not file_path_obj.exists() or not file_path_obj.is_file():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        # 디렉토리 파라미터 처리
        directory_path = None
        if directory:
            directory_path = Path(directory)
            if not directory_path.is_absolute():
                directory_path = Path.cwd() / directory_path
            directory_path.mkdir(parents=True, exist_ok=True)
        
        # 구조 분석 결과 파일 경로
        output_dir = parser_service.get_output_directory(file_path_obj, directory_path)
        structure_result_path = output_dir / ("llm_structure_analysis.json" if use_llm else "structure_analysis.json")
        
        # 기존 구조 분석 결과 확인
        if not force_reanalyze and structure_result_path.exists():
            with open(structure_result_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path_obj, directory_path) or force_reparse:
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path_obj,
                force_reparse=force_reparse,
                directory=directory_path
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path_obj, directory_path)
            
        # Markdown 파일들을 올바른 위치로 이동 (기존 파싱 결과 로드 시에도 필요)
        if parsing_results.get("parsing_results"):
            _move_markdown_files_to_correct_location(parsing_results, file_path_obj, output_dir)
        
        # 2. 구조 분석 수행
        if use_llm:
            # LLM 기반 구조 분석 수행
            # 최고 품질 파서의 텍스트 사용
            best_parser = parsing_results.get("summary", {}).get("best_parser")
            document_text = ""
            if best_parser and best_parser in parsing_results.get("parsing_results", {}):
                parser_dir = output_dir / best_parser
                text_file = parser_dir / f"{best_parser}_text.txt"
                if text_file.exists():
                    with open(text_file, 'r', encoding='utf-8') as f:
                        document_text = f.read()
            
            structure_analysis = analyzer.analyze_document_structure_with_llm(
                text=document_text,
                file_path=str(file_path_obj),
                file_extension=file_path_obj.suffix.lower()
            )

            # LLM 분석 결과 검증
            if not structure_analysis or not structure_analysis.get("llm_analysis"):
                raise HTTPException(
                    status_code=500,
                    detail="LLM 구조 분석이 실패했습니다. JSON 파싱 오류 또는 LLM 응답 오류가 발생했습니다."
                )

            # 파싱 정보 추가
            structure_analysis["file_info"] = parsing_results["file_info"]
            structure_analysis["analysis_timestamp"] = datetime.now().isoformat()
            structure_analysis["source_parser"] = best_parser
            
        else:
            # 기존 기본 구조 분석 수행
            structure_analysis = {
                "file_info": parsing_results["file_info"],
                "analysis_timestamp": datetime.now().isoformat(),
                "structure_elements": {},
                "summary": {
                    "total_elements": 0,
                    "element_types": {},
                    "complexity_score": 0
                }
            }
        
        # 기본 구조 분석의 경우에만 파서별 구조 정보 수집
        if not use_llm:
            # 각 파서별 구조 정보 수집
            for parser_name, parser_result in parsing_results.get("parsing_results", {}).items():
                if not parser_result.get("success"):
                    continue
                    
                elements = {}
                
                # 구조화된 정보가 있는 경우 활용
                if parser_result.get("structured_info"):
                    structured_info = parser_result["structured_info"]
                    
                    # 기본 구조 요소들
                    elements.update({
                        "total_lines": structured_info.get("total_lines", 0),
                        "paragraphs": structured_info.get("paragraphs", 0),
                        "headers": structured_info.get("headers", 0),
                        "non_empty_lines": structured_info.get("non_empty_lines", 0)
                    })
                    
                    # Docling 파서의 경우 추가 구조 정보
                    if parser_name == "docling" and "document_structure" in structured_info:
                        doc_structure = structured_info["document_structure"]
                        elements.update({
                            "tables": doc_structure.get("tables", []),
                            "images": doc_structure.get("images", []),
                            "sections": doc_structure.get("sections", []),
                            "table_count": len(doc_structure.get("tables", [])),
                            "image_count": len(doc_structure.get("images", [])),
                            "section_count": len(doc_structure.get("sections", []))
                        })
                
                # 텍스트 기반 추가 분석 (모든 파서에 대해)
                if "text_length" in parser_result:
                    text_length = parser_result["text_length"]
                    word_count = parser_result.get("word_count", 0)
                    
                    # 복잡도 점수 계산
                    complexity = 0
                    if word_count > 0:
                        complexity += min(word_count / 1000, 1.0) * 0.4  # 단어 수 기반
                    if elements.get("headers", 0) > 0:
                        complexity += min(elements["headers"] / 10, 1.0) * 0.3  # 헤더 수 기반
                    if elements.get("table_count", 0) > 0:
                        complexity += min(elements["table_count"] / 5, 1.0) * 0.3  # 테이블 수 기반
                        
                    elements["complexity_score"] = complexity
                
                structure_analysis["structure_elements"][parser_name] = elements
            
            # 전체 요약 계산 (기본 분석의 경우에만)
            all_elements = structure_analysis["structure_elements"]
            if all_elements:
                # 가장 복잡도가 높은 파서의 결과를 기준으로 요약
                best_parser = max(all_elements.keys(), 
                                key=lambda p: all_elements[p].get("complexity_score", 0))
                best_elements = all_elements[best_parser]
                
                structure_analysis["summary"] = {
                    "best_parser": best_parser,
                    "total_elements": sum(1 for k, v in best_elements.items() 
                                        if isinstance(v, int) and v > 0),
                    "element_types": {k: v for k, v in best_elements.items() 
                                    if isinstance(v, int) and v > 0},
                    "complexity_score": best_elements.get("complexity_score", 0),
                    "has_tables": best_elements.get("table_count", 0) > 0,
                    "has_images": best_elements.get("image_count", 0) > 0,
                    "has_sections": best_elements.get("section_count", 0) > 0
                }
        
        # 결과 저장
        output_dir.mkdir(exist_ok=True)
        with open(structure_result_path, 'w', encoding='utf-8') as f:
            json.dump(structure_analysis, f, ensure_ascii=False, indent=2)
        
        # 저장된 파일 경로 수집
        saved_files = []
        
        # 구조 분석 결과 파일
        saved_files.append({
            "type": "structure_analysis",
            "path": str(structure_result_path),
            "description": "LLM 기반 구조 분석 결과" if use_llm else "기본 구조 분석 결과"
        })
        
        # 파싱 관련 파일들
        if parsing_results.get("parsing_results"):
            for parser_name, parser_result in parsing_results["parsing_results"].items():
                if parser_result.get("success"):
                    parser_dir = output_dir / parser_name
                    
                    # 텍스트 파일
                    text_file = parser_dir / f"{parser_name}_text.txt"
                    if text_file.exists():
                        saved_files.append({
                            "type": "extracted_text",
                            "parser": parser_name,
                            "path": str(text_file),
                            "description": f"{parser_name} 파서로 추출된 텍스트"
                        })
                    
                    # 메타데이터 파일
                    metadata_file = parser_dir / f"{parser_name}_metadata.json"
                    if metadata_file.exists():
                        saved_files.append({
                            "type": "metadata",
                            "parser": parser_name,
                            "path": str(metadata_file),
                            "description": f"{parser_name} 파서 메타데이터"
                        })
                    
                    # 구조 정보 파일
                    structure_file = parser_dir / f"{parser_name}_structure.json"
                    if structure_file.exists():
                        saved_files.append({
                            "type": "parser_structure",
                            "parser": parser_name,
                            "path": str(structure_file),
                            "description": f"{parser_name} 파서 구조 정보"
                        })
                    
                    # Markdown 파일들 확인 (Docling, PyMuPDF4LLM)
                    if parser_name == "docling":
                        # Docling markdown 파일
                        md_file = output_dir / "docling.md"
                        if md_file.exists():
                            saved_files.append({
                                "type": "markdown",
                                "parser": parser_name,
                                "path": str(md_file),
                                "description": "Docling 파서로 생성된 Markdown"
                            })
                    elif parser_name == "pdf_parser":
                        # PyMuPDF4LLM markdown 파일 (pdf_parser 내에서 생성됨)
                        pymupdf_md_file = output_dir / "pymupdf4llm.md"
                        if pymupdf_md_file.exists():
                            saved_files.append({
                                "type": "markdown",
                                "parser": "pymupdf4llm",
                                "path": str(pymupdf_md_file),
                                "description": "PyMuPDF4LLM 파서로 생성된 Markdown"
                            })
        
        # 파싱 결과 종합 파일
        parsing_result_path = parser_service.get_parsing_result_path(file_path_obj, directory_path)
        if parsing_result_path.exists():
            saved_files.append({
                "type": "parsing_summary",
                "path": str(parsing_result_path),
                "description": "파싱 결과 종합"
            })
        
        # 응답에 파일 경로 정보 추가
        structure_analysis["saved_files"] = saved_files
        structure_analysis["output_directory"] = str(output_dir)
        
        return structure_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        from utils.error_handler import log_and_raise_http_exception, collect_context_info
        
        # 컨텍스트 정보 수집
        context = collect_context_info(locals())
        
        # 상세한 오류 로깅 및 HTTPException 발생
        log_and_raise_http_exception(
            e, 
            "문서 구조 분석", 
            context=context,
            logger_name=__name__
        )


@router.get("/structure-analysis")
async def get_structure_analysis(
    file_path: str = Query(..., description="구조 분석 결과를 조회할 파일 경로"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    force_reanalyze: bool = Query(False, description="재분석 여부"),
    use_llm: bool = Query(False, description="LLM 기반 구조 분석 사용 여부"),
    directory: Optional[str] = Query(None, description="출력 디렉토리 경로"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 문서 구조 분석을 수행하거나 조회합니다.
    
    Parameters:
    - file_path: 분석할 파일 경로
    - force_reparse: 기존 파싱 결과 무시하고 재파싱 수행
    - force_reanalyze: 기존 구조 분석 결과 무시하고 재분석 수행
    - use_llm: LLM을 사용한 고급 구조 분석 수행 (기본값: False)
    - directory: 결과 파일을 저장할 디렉토리 (기본값: 파일명 기반)
    """
    request = {
        "file_path": file_path,
        "force_reparse": force_reparse,
        "force_reanalyze": force_reanalyze,
        "use_llm": use_llm,
        "directory": directory
    }
    
    return await analyze_document_structure(request, db)


def _integrate_llm_structure_into_kg(kg_result: Dict[str, Any], llm_analysis: Dict[str, Any], file_path: str, dataset_id: str = None) -> Dict[str, Any]:
    """
    LLM 구조 분석 결과를 Knowledge Graph에 통합합니다.
    structureAnalysis 섹션만 사용하여 깨끗한 지식 그래프를 구축합니다.
    
    Args:
        kg_result: 기존 KG 결과
        llm_analysis: LLM 구조 분석 결과
        file_path: 문서 파일 경로
    
    Returns:
        통합된 KG 결과
    """
    import hashlib
    import os
    
    def _hash(s: str) -> str:
        # None 또는 빈 값 처리
        if s is None:
            s = ""
        elif not isinstance(s, str):
            s = str(s)
        return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]
    
    # 타입 안전성 확인
    if not isinstance(kg_result, dict) or not isinstance(llm_analysis, dict):
        return kg_result
    
    if not llm_analysis:
        return kg_result
    
    # structureAnalysis만 사용하므로 새로운 엔티티/관계 리스트로 시작
    entities = []
    relationships = []
    structural_hierarchy = []
    
    # 문서 노드 생성 (structureAnalysis 전용)
    doc_info = llm_analysis.get("documentInfo", {})
    doc_entity_id = f"doc_{_hash(file_path)}"
    
    # 문서 엔티티 생성
    doc_properties = {
        "title": doc_info.get("title", "") if doc_info else os.path.basename(file_path),
        "document_type": doc_info.get("documentType", "") if doc_info else "document",
        "file_path": file_path,
        "publication_date": doc_info.get("publicationInfo", {}).get("publicationDate", "") if doc_info else "",
        "publishing_institution": doc_info.get("publicationInfo", {}).get("publishingInstitution", "") if doc_info else ""
    }
    
    # dataset_id가 있으면 추가
    if dataset_id:
        doc_properties["dataset_id"] = dataset_id
    
    doc_entity = {
        "id": doc_entity_id,
        "type": "Document",
        "properties": doc_properties
    }
    entities.append(doc_entity)
    
    # structureAnalysis의 계층적 문서 구조를 그래프로 구성
    for section_idx, section in enumerate(llm_analysis.get("structureAnalysis", [])):
        # 메인 섹션 엔티티
        section_properties = {
            "title": section.get("title", ""),
            "unit": section.get("unit", ""),
            "content": section.get("mainContent", ""),
            "keywords": section.get("keywords", []),
            "page": section.get("page", ""),
            "section_index": section_idx,
            "hierarchical_level": 1,
            "section_type": "main_section"
        }
        
        # dataset_id가 있으면 추가
        if dataset_id:
            section_properties["dataset_id"] = dataset_id
        
        # title이 None인 경우 처리
        section_title = section.get('title')
        if section_title is None:
            section_title = f"Section_{section_idx}"
            
        section_entity = {
            "id": f"llm_section_{_hash(section_title)}_{section_idx}",
            "type": "DocumentSection",
            "properties": section_properties
        }
        entities.append(section_entity)
        
        # 문서-섹션 관계
        relationships.append({
            "id": f"rel_{_hash(doc_entity_id + section_entity['id'])}",
            "type": "CONTAINS_SECTION",
            "source": doc_entity_id,
            "target": section_entity["id"],
            "properties": {
                "unit": section.get("unit", ""),
                "section_index": section_idx,
                "relationship_type": "document_structure"
            }
        })
        
        # 섹션의 키워드들을 개별 엔티티로 추가하고 관계 설정
        for keyword in section.get("keywords", []):
            keyword_properties = {
                "text": keyword,
                "source_section": section.get("title", ""),
                "section_unit": section.get("unit", ""),
                "extraction_method": "llm_structure_analysis"
            }
            
            # dataset_id가 있으면 추가
            if dataset_id:
                keyword_properties["dataset_id"] = dataset_id
            
            keyword_entity = {
                "id": f"llm_keyword_{_hash(keyword)}_{section_idx}",
                "type": "SectionKeyword",
                "properties": keyword_properties
            }
            entities.append(keyword_entity)
            
            # 섹션-키워드 관계
            relationships.append({
                "id": f"rel_{_hash(section_entity['id'] + keyword_entity['id'])}",
                "type": "HAS_KEYWORD",
                "source": section_entity["id"],
                "target": keyword_entity["id"],
                "properties": {"extraction_source": "section_content"}
            })
        
        # 하위 구조 (subStructure) 처리
        for subsection_idx, subsection in enumerate(section.get("subStructure", [])):
            subsection_properties = {
                "title": subsection.get("title", ""),
                "unit": subsection.get("unit", ""),
                "content": subsection.get("mainContent", ""),
                "keywords": subsection.get("keywords", []),
                "parent_section": section.get("title", ""),
                "subsection_index": subsection_idx,
                "hierarchical_level": 2,
                "section_type": "subsection"
            }
            
            # dataset_id가 있으면 추가
            if dataset_id:
                subsection_properties["dataset_id"] = dataset_id
            
            subsection_entity = {
                "id": f"llm_subsection_{_hash(subsection.get('title', ''))}_{section_idx}_{subsection_idx}",
                "type": "DocumentSubsection",
                "properties": subsection_properties
            }
            entities.append(subsection_entity)
            
            # 섹션-하위섹션 관계
            relationships.append({
                "id": f"rel_{_hash(section_entity['id'] + subsection_entity['id'])}",
                "type": "HAS_SUBSECTION",
                "source": section_entity["id"],
                "target": subsection_entity["id"],
                "properties": {
                    "unit": subsection.get("unit", ""),
                    "subsection_index": subsection_idx,
                    "relationship_type": "hierarchical_structure"
                }
            })
            
            # 하위섹션의 키워드들을 개별 엔티티로 추가
            for keyword in subsection.get("keywords", []):
                subsection_keyword_entity = {
                    "id": f"llm_sub_keyword_{_hash(keyword)}_{section_idx}_{subsection_idx}",
                    "type": "SubsectionKeyword",
                    "properties": {
                        "text": keyword,
                        "source_subsection": subsection.get("title", ""),
                        "parent_section": section.get("title", ""),
                        "subsection_unit": subsection.get("unit", ""),
                        "extraction_method": "llm_structure_analysis"
                    }
                }
                entities.append(subsection_keyword_entity)
                
                # 하위섹션-키워드 관계
                relationships.append({
                    "id": f"rel_{_hash(subsection_entity['id'] + subsection_keyword_entity['id'])}",
                    "type": "HAS_KEYWORD",
                    "source": subsection_entity["id"],
                    "target": subsection_keyword_entity["id"],
                    "properties": {"extraction_source": "subsection_content"}
                })
    
    # structureAnalysis만 사용하므로 coreContent, keyData 등은 제거
    # 오직 문서 구조(섹션, 하위섹션, 키워드)만 그래프로 구성
    
    return {
        **kg_result,
        "entities": entities,
        "relationships": relationships,
        "structural_hierarchy": structural_hierarchy
    }


@router.post("/knowledge-graph")
async def generate_knowledge_graph(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    문서로부터 Knowledge Graph를 생성하고 저장된 파일 정보를 반환합니다.

    - 파싱 및 키워드 추출 결과를 활용하여 KG를 생성합니다
    - 생성된 결과는 파일로 저장되며 기본적으로 재사용됩니다
    - force_* 옵션이 없는 경우 기존 결과를 바로 반환합니다
    - 응답은 saved_files 목록과 통계 정보만 포함합니다
    - dataset_id가 제공되면 모든 노드에 dataset 프로퍼티가 추가됩니다
    """
    from pathlib import Path
    import json
    from services.kg_builder import KGBuilder
    
    file_path = request.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="파일 경로가 필요합니다")
    
    # 파일 경로 초기 검증
    file_path_obj = Path(file_path)
    if not file_path_obj.is_absolute():
        file_path_obj = Path.cwd() / file_path_obj
    
    # 즉시 파일 경로 검증
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
    
    if file_path_obj.is_dir():
        raise HTTPException(status_code=400, detail=f"디렉토리가 아닌 파일이어야 합니다: {file_path}")
    
    if file_path_obj.stat().st_size == 0:
        raise HTTPException(status_code=400, detail=f"파일이 비어있습니다: {file_path}")
    
    # 지원되는 파일 형식인지 확인
    supported_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md', '.html', '.xml', '.hwp'}
    if file_path_obj.suffix.lower() not in supported_extensions:
        raise HTTPException(status_code=400, detail=f"지원되지 않는 파일 형식입니다: {file_path_obj.suffix}")
    
    try:
        # 파일 접근 권한 확인
        with open(file_path_obj, 'rb') as f:
            f.read(1)  # 1바이트 읽기 테스트
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"파일 접근 권한이 없습니다: {file_path}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일을 읽을 수 없습니다: {str(e)}")
    
    force_reparse = request.get("force_reparse", False)
    force_reanalyze = request.get("force_reanalyze", False)
    force_rebuild = request.get("force_rebuild", False)
    use_llm = request.get("use_llm", True)  # LLM 기반 분석 옵션 (기본값: True)
    llm_overrides = request.get("llm") or request.get("llm_config")  # 단일 요청용 LLM 설정
    if use_llm and isinstance(llm_overrides, dict) and "enabled" not in llm_overrides:
        llm_overrides["enabled"] = True
    directory = request.get("directory")
    dataset_id = request.get("dataset_id")  # 선택적 dataset_id 파라미터
    
    parser_service = DocumentParserService()
    analyzer = LocalFileAnalyzer(db)
    
    try:
        # 디렉토리 파라미터 처리
        directory_path = None
        if directory:
            directory_path = Path(directory)
            if not directory_path.is_absolute():
                directory_path = Path.cwd() / directory_path
            directory_path.mkdir(parents=True, exist_ok=True)
        
        # Knowledge Graph 결과 파일 경로들
        output_dir = parser_service.get_output_directory(file_path_obj, directory_path)
        kg_result_path = output_dir / "knowledge_graph.json"  # 전체 KG 데이터
        kg_response_path = output_dir / "knowledge_graph_response.json"  # API 응답용

        # force 옵션이 없고 기존 응답이 있는 경우 바로 반환
        if not any([force_reparse, force_reanalyze, force_rebuild]) and kg_response_path.exists():
            with open(kg_response_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        parsing_results = {}
        try:
            if not parser_service.has_parsing_results(file_path_obj, directory_path) or force_reparse:
                parsing_results = parser_service.parse_document_comprehensive(
                    file_path=file_path_obj,
                    force_reparse=force_reparse,
                    directory=directory_path
                )
            else:
                parsing_results = parser_service.load_existing_parsing_results(file_path_obj, directory_path)
        except Exception as parsing_error:
            # 파싱 실패 시 빈 결과로 계속 진행
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ 파싱 실패, 빈 결과로 KG 생성 진행: {parsing_error}")
            parsing_results = {
                "parsing_results": {},
                "summary": {"success": False, "best_parser": None, "error": str(parsing_error)},
                "file_info": {
                    "name": file_path_obj.name,
                    "path": str(file_path_obj),
                    "size": file_path_obj.stat().st_size if file_path_obj.exists() else 0,
                    "extension": file_path_obj.suffix.lower()
                }
            }
            
        # Markdown 파일들을 올바른 위치로 이동 (기존 파싱 결과 로드 시에도 필요)
        if parsing_results.get("parsing_results"):
            _move_markdown_files_to_correct_location(parsing_results, file_path_obj, output_dir)
        
        # 2. 구조 분석 수행 (KG 구축의 필수 전제조건)
        structure_result_path = output_dir / ("llm_structure_analysis.json" if use_llm else "structure_analysis.json")
        structure_results = {}
        
        # 구조 분석이 없거나 force_rebuild인 경우 구조 분석 수행
        if not structure_result_path.exists() or force_rebuild or force_reanalyze:
            # 텍스트 추출
            best_parser = parsing_results.get("summary", {}).get("best_parser")
            document_text = ""
            if best_parser and best_parser in parsing_results.get("parsing_results", {}):
                parser_dir = parser_service.get_output_directory(file_path_obj, directory_path) / best_parser
                text_file = parser_dir / f"{best_parser}_text.txt"
                if text_file.exists():
                    with open(text_file, 'r', encoding='utf-8') as f:
                        document_text = f.read()
            
            if use_llm:
                # LLM 기반 구조 분석 수행
                structure_results = analyzer.analyze_document_structure_with_llm(
                    text=document_text,
                    file_path=str(file_path_obj),
                    file_extension=file_path_obj.suffix.lower(),
                    overrides=llm_overrides
                )
            else:
                # 기본 구조 분석 수행
                structure_results = analyzer.analyze_document_structure(
                    text=document_text,
                    file_extension=file_path_obj.suffix
                )
            
            # 파싱 정보 추가
            structure_results["file_info"] = parsing_results["file_info"]
            structure_results["analysis_timestamp"] = datetime.now().isoformat()
            structure_results["source_parser"] = best_parser
            
            # 구조 분석 결과 저장
            with open(structure_result_path, 'w', encoding='utf-8') as f:
                json.dump(structure_results, f, ensure_ascii=False, indent=2)
        else:
            with open(structure_result_path, 'r', encoding='utf-8') as f:
                structure_results = json.load(f)
        
        # 3. 키워드 추출 결과 확인 및 필요시 분석 수행
        analysis_result_path = output_dir / "keyword_analysis.json"
        if use_llm:
            # LLM 모드에서는 구조 분석 내 키워드를 사용하므로 별도 키워드 추출을 생략
            analysis_results = {"keywords": {}}
        else:
            if not force_reanalyze and analysis_result_path.exists():
                with open(analysis_result_path, 'r', encoding='utf-8') as f:
                    analysis_results = json.load(f)
            else:
                # 키워드 추출 수행
                result = analyzer.analyze_file(
                    file_path=str(file_path_obj),
                    extractors=None,  # 모든 추출기 사용
                    force_reanalyze=force_reanalyze
                )
                analysis_results = result
        
        # 4. 계층적 Knowledge Graph 생성
        from services.hierarchical_kg_builder import HierarchicalKGBuilder
        # LLM을 사용할 경우 자동 Memgraph 저장을 비활성화 (향상된 버전을 나중에 저장)
        kg_builder = HierarchicalKGBuilder(db_session=db, auto_save_to_memgraph=not use_llm, llm_config=llm_overrides if llm_overrides else None)
        
        # 최고 품질 파서의 텍스트 사용  
        best_parser = parsing_results.get("summary", {}).get("best_parser")
        if best_parser and best_parser in parsing_results.get("parsing_results", {}):
            parser_result = parsing_results["parsing_results"][best_parser]
            # 개별 파서 텍스트 파일에서 읽기
            parser_dir = output_dir / best_parser
            text_file = parser_dir / f"{best_parser}_text.txt"
            
            if text_file.exists():
                with open(text_file, 'r', encoding='utf-8') as f:
                    document_text = f.read()
            else:
                document_text = ""
        else:
            document_text = ""
        
        # 계층적 KG 생성 - 문서 구조 기반
        # LLM 모드일 때는 키워드를 사용하지 않음 (structureAnalysis만 사용)
        kg_result = kg_builder.build_hierarchical_knowledge_graph(
            file_path=str(file_path_obj),
            document_text=document_text,
            keywords={} if use_llm else analysis_results.get("keywords", {}),
            metadata=parsing_results.get("file_info", {}),
            structure_analysis=structure_results,
            parsing_results=parsing_results,
            force_rebuild=force_rebuild,
            dataset_id=dataset_id  # dataset_id 전달
        )
        
        # LLM 구조 분석 결과를 KG에 통합
        if use_llm and structure_results.get("llm_analysis"):
            llm_analysis = structure_results["llm_analysis"]
            # structureAnalysis가 비어있는지 확인
            if llm_analysis.get("structureAnalysis") and len(llm_analysis["structureAnalysis"]) > 0:
                kg_result = _integrate_llm_structure_into_kg(kg_result, llm_analysis, str(file_path_obj), dataset_id)
            else:
                # structureAnalysis가 비어있으면 기본 문서 엔티티만 생성
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("⚠️ LLM structureAnalysis가 비어있어 기본 문서 엔티티만 생성합니다.")
                
                # 기본 문서 엔티티 생성
                import hashlib
                import os
                def _hash(s: str) -> str:
                    # None 또는 빈 값 처리
                    if s is None:
                        s = ""
                    elif not isinstance(s, str):
                        s = str(s)
                    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:16]
                
                doc_info = llm_analysis.get("documentInfo", {})
                doc_entity_id = f"doc_{_hash(str(file_path_obj))}"
                
                # 기본 문서 엔티티 properties 생성
                doc_properties = {
                    "title": doc_info.get("title", "") if doc_info else os.path.basename(str(file_path_obj)),
                    "document_type": doc_info.get("documentType", "") if doc_info else "document",
                    "file_path": str(file_path_obj),
                    "parsing_status": "failed",
                    "note": "PDF 파싱 실패로 구조 분석 불가"
                }
                
                # dataset_id가 있으면 추가
                if dataset_id:
                    doc_properties["dataset_id"] = dataset_id
                
                kg_result = {
                    "entities": [{
                        "id": doc_entity_id,
                        "type": "Document",
                        "properties": doc_properties
                    }],
                    "relationships": [],
                    "structural_hierarchy": []
                }
        elif use_llm and not structure_results.get("llm_analysis"):
            # LLM 분석 자체가 실패한 경우 - 기본 KG 결과로 계속 진행 (500 반환 대신 경고)
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("⚠️ LLM 구조 분석이 실패하여 기본 KG 결과로 반환합니다.")
            # 최소한의 메타데이터에 실패 정보 기록
            if isinstance(kg_result, dict):
                kg_result.setdefault("metadata", {})
                kg_result["metadata"]["llm_success"] = False
                if isinstance(structure_results, dict) and structure_results.get("llm_error"):
                    kg_result["metadata"]["llm_error"] = structure_results.get("llm_error")
        
        # LLM 구조 통합 완료 후 향상된 KG를 Memgraph에 저장
        if use_llm and isinstance(kg_result, dict):
            try:
                import logging
                logger = logging.getLogger(__name__)
                
                # 향상된 엔티티 타입 목록 확인
                entity_types = set()
                for entity in kg_result.get('entities', []):
                    entity_types.add(entity.get('type', 'Unknown'))
                
                logger.info(f"🔄 LLM 향상된 KG를 Memgraph에 저장 시도 중...")
                logger.info(f"📊 총 엔티티: {len(kg_result.get('entities', []))}, 총 관계: {len(kg_result.get('relationships', []))}")
                logger.info(f"📝 엔티티 타입 목록: {', '.join(sorted(entity_types))}")
                
                # DocumentSection 등 LLM 엔티티 개수 확인
                llm_entities = [e for e in kg_result.get('entities', []) if e.get('type') in ['DocumentSection', 'DocumentSubsection', 'Author', 'Topic', 'Statistic']]
                logger.info(f"🎯 LLM 특화 엔티티: {len(llm_entities)}개")
                
                # memgraph_service = MemgraphService()
                
                if False and memgraph_service.is_connected():
                    # 기존 데이터 완전히 삭제하고 새로 저장
                    logger.info("🗑️ 기존 Memgraph 데이터 삭제 및 향상된 KG 저장 중 (clear_existing=True)...")
                    success = memgraph_service.insert_kg_data(kg_result, clear_existing=True)
                    
                    if success:
                        if "metadata" not in kg_result:
                            kg_result["metadata"] = {}
                        kg_result["metadata"]["memgraph_enhanced_saved"] = True
                        kg_result["metadata"]["memgraph_enhanced_saved_at"] = datetime.now().isoformat()
                        kg_result["metadata"]["memgraph_enhanced_entities"] = len(kg_result.get("entities", []))
                        kg_result["metadata"]["memgraph_enhanced_relationships"] = len(kg_result.get("relationships", []))
                        logger.info(f"✅ Memgraph에 향상된 KG 저장 성공! (엔티티: {len(kg_result.get('entities', []))}, 관계: {len(kg_result.get('relationships', []))})")
                    else:
                        if "metadata" not in kg_result:
                            kg_result["metadata"] = {}
                        kg_result["metadata"]["memgraph_enhanced_saved"] = False
                        logger.warning("⚠️ Memgraph에 향상된 KG 저장 실패")
                else:
                    if "metadata" not in kg_result:
                        kg_result["metadata"] = {}
                    kg_result["metadata"]["memgraph_enhanced_saved"] = False
                    kg_result["metadata"]["memgraph_error"] = "Connection failed"
                    logger.error("❌ Memgraph 연결 실패")
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"❌ Memgraph 향상된 KG 저장 중 오류: {e}")
                if "metadata" not in kg_result:
                    kg_result["metadata"] = {}
                kg_result["metadata"]["memgraph_enhanced_saved"] = False
                kg_result["metadata"]["memgraph_enhanced_error"] = str(e)
        
        # 계층적 KG 결과에 추가 정보 포함
        kg_with_context = {
            "file_info": parsing_results["file_info"],
            "generation_timestamp": datetime.now().isoformat(),
            "source_parser": best_parser,
            "keywords_used": len(analysis_results.get("keywords", {})),
            "llm_structure_integrated": use_llm and "llm_analysis" in structure_results,
            "knowledge_graph": kg_result,
            "statistics": {
                "total_entities": len(kg_result.get("entities", [])),
                "total_relationships": len(kg_result.get("relationships", [])),
                "structural_elements": len(kg_result.get("structural_hierarchy", [])),
                "entity_types": {},
                "relationship_types": {}
            }
        }
        
        # 엔티티 타입별 통계
        entity_types = {}
        for entity in kg_result.get("entities", []):
            entity_type = entity.get("type", "unknown")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        kg_with_context["statistics"]["entity_types"] = entity_types
        
        # 관계 타입별 통계
        relationship_types = {}
        for rel in kg_result.get("relationships", []):
            rel_type = rel.get("type", "unknown")
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
        kg_with_context["statistics"]["relationship_types"] = relationship_types
        
        # 결과 저장
        output_dir.mkdir(exist_ok=True)
        with open(kg_result_path, 'w', encoding='utf-8') as f:
            json.dump(kg_with_context, f, ensure_ascii=False, indent=2)
        
        # 저장된 파일 경로 수집
        saved_files = []
        
        # Knowledge Graph 결과 파일
        saved_files.append({
            "type": "knowledge_graph",
            "path": str(kg_result_path),
            "description": "계층적 Knowledge Graph 결과"
        })
        
        # 구조 분석 결과 파일
        structure_result_path = output_dir / ("llm_structure_analysis.json" if use_llm else "structure_analysis.json")
        if structure_result_path.exists():
            saved_files.append({
                "type": "structure_analysis",
                "path": str(structure_result_path),
                "description": "문서 구조 분석 결과"
            })
        
        # 키워드 분석 결과 파일
        analysis_result_path = output_dir / "keyword_analysis.json"
        if analysis_result_path.exists():
            saved_files.append({
                "type": "keyword_analysis",
                "path": str(analysis_result_path),
                "description": "키워드 분석 결과"
            })
        
        # 파싱 관련 파일들
        if parsing_results.get("parsing_results"):
            for parser_name, parser_result in parsing_results["parsing_results"].items():
                if parser_result.get("success"):
                    parser_dir = output_dir / parser_name
                    
                    # 텍스트 파일
                    text_file = parser_dir / f"{parser_name}_text.txt"
                    if text_file.exists():
                        saved_files.append({
                            "type": "extracted_text",
                            "parser": parser_name,
                            "path": str(text_file),
                            "description": f"{parser_name} 파서로 추출된 텍스트"
                        })
                    
                    # 메타데이터 파일
                    metadata_file = parser_dir / f"{parser_name}_metadata.json"
                    if metadata_file.exists():
                        saved_files.append({
                            "type": "metadata",
                            "parser": parser_name,
                            "path": str(metadata_file),
                            "description": f"{parser_name} 파서 메타데이터"
                        })
                    
                    # 구조 정보 파일
                    structure_file = parser_dir / f"{parser_name}_structure.json"
                    if structure_file.exists():
                        saved_files.append({
                            "type": "parser_structure",
                            "parser": parser_name,
                            "path": str(structure_file),
                            "description": f"{parser_name} 파서 구조 정보"
                        })
        
        # 파싱 결과 종합 파일
        parsing_result_path = parser_service.get_parsing_result_path(file_path_obj, directory_path)
        if parsing_result_path.exists():
            saved_files.append({
                "type": "parsing_summary",
                "path": str(parsing_result_path),
                "description": "파싱 결과 종합"
            })
        
        # Memgraph 저장 상태 정보
        if kg_result.get("memgraph_saved"):
            saved_files.append({
                "type": "memgraph_database",
                "path": "memgraph://localhost:7687",
                "description": "Memgraph 그래프 데이터베이스에 저장된 KG 데이터"
            })
        
        # 응답에 파일 경로 정보 추가
        kg_with_context["saved_files"] = saved_files
        kg_with_context["output_directory"] = str(output_dir)

        # API 응답용 데이터 생성 (saved_files만 포함)
        api_response = {
            "saved_files": saved_files,
            "output_directory": str(output_dir),
            "generation_timestamp": datetime.now().isoformat(),
            "statistics": {
                "total_saved_files": len(saved_files),
                "file_types": {}
            }
        }

        # 파일 타입별 통계
        file_types = {}
        for file_info in saved_files:
            file_type = file_info.get("type", "unknown")
            file_types[file_type] = file_types.get(file_type, 0) + 1
        api_response["statistics"]["file_types"] = file_types

        # API 응답 저장 (saved_files 중심)
        with open(kg_response_path, 'w', encoding='utf-8') as f:
            json.dump(api_response, f, ensure_ascii=False, indent=2)

        return api_response
        
    except HTTPException:
        raise
    except Exception as e:
        from utils.error_handler import log_and_raise_http_exception, collect_context_info
        
        # 컨텍스트 정보 수집
        context = collect_context_info(locals())
        
        # 상세한 오류 로깅 및 HTTPException 발생
        log_and_raise_http_exception(
            e, 
            "Knowledge Graph 생성", 
            context=context,
            logger_name=__name__
        )


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    file_path: str = Query(..., description="Knowledge Graph를 조회할 파일 경로"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    force_reanalyze: bool = Query(False, description="재분석 여부"),
    force_rebuild: bool = Query(False, description="KG 재생성 여부"),
    use_llm: bool = Query(True, description="LLM 기반 구조 분석 사용 여부 (기본값: True)"),
    directory: Optional[str] = Query(None, description="결과 저장 디렉토리"),
    dataset_id: Optional[str] = Query(None, description="데이터셋 ID (선택적, 모든 노드에 dataset 프로퍼티 추가)"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 Knowledge Graph를 생성하고 저장된 파일 정보를 반환합니다.

    - 기존 결과가 있고 force 옵션이 없으면 저장된 응답을 바로 반환
    - 응답은 saved_files 목록과 통계 정보만 포함합니다
    - dataset_id가 제공되면 모든 노드에 dataset 프로퍼티가 추가됩니다
    """
    request = {
        "file_path": file_path,
        "force_reparse": force_reparse,
        "force_reanalyze": force_reanalyze,
        "force_rebuild": force_rebuild,
        "use_llm": use_llm,
        "directory": directory,
        "dataset_id": dataset_id
    }
    
    return await generate_knowledge_graph(request, db)


@router.get("/config/root")
async def get_file_root(db: Session = Depends(get_db)):
    """
    현재 설정된 파일 루트 디렉토리를 조회합니다.
    """
    analyzer = LocalFileAnalyzer(db)
    return {"file_root": analyzer.get_file_root()}


@router.get("/config/current-directory")
async def get_current_directory():
    """
    백엔드 서버의 현재 작업 디렉토리를 조회합니다.
    """
    import os
    from pathlib import Path
    
    current_dir = Path.cwd()
    parent_dir = current_dir.parent
    
    # 현재 디렉토리의 파일 목록 수집
    files = []
    directories = []
    
    try:
        for item in current_dir.iterdir():
            item_info = {
                "name": item.name,
                "path": str(item),
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime,
                "is_hidden": item.name.startswith(".")
            }
            
            if item.is_file():
                item_info["extension"] = item.suffix.lower()
                files.append(item_info)
            elif item.is_dir():
                try:
                    # 디렉토리 내 항목 개수 계산
                    item_count = len(list(item.iterdir()))
                    item_info["item_count"] = item_count
                except (PermissionError, OSError):
                    item_info["item_count"] = 0
                directories.append(item_info)
    except (PermissionError, OSError):
        pass  # 권한 오류 시 빈 목록 반환
    
    # 이름순 정렬
    files.sort(key=lambda x: x["name"].lower())
    directories.sort(key=lambda x: x["name"].lower())
    
    return {
        "current_directory": str(current_dir),
        "parent_directory": str(parent_dir),
        "relative_to_parent": "../",
        "working_directory_info": {
            "name": current_dir.name,
            "exists": current_dir.exists(),
            "is_directory": current_dir.is_dir()
        },
        "contents": {
            "directories": directories,
            "files": files,
            "total_directories": len(directories),
            "total_files": len(files)
        }
    }


@router.post("/config/change-directory")
async def change_directory(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    현재 작업 디렉토리를 변경합니다.
    """
    import os
    from pathlib import Path
    
    new_directory = request.get("directory")
    if not new_directory:
        raise HTTPException(status_code=400, detail="디렉토리 경로가 필요합니다")
    
    new_path = Path(new_directory)
    
    # 절대 경로로 변환
    if not new_path.is_absolute():
        new_path = Path.cwd() / new_path
    
    # 디렉토리 존재 여부 확인
    if not new_path.exists():
        raise HTTPException(status_code=404, detail=f"디렉토리를 찾을 수 없습니다: {new_path}")
    
    if not new_path.is_dir():
        raise HTTPException(status_code=400, detail=f"경로가 디렉토리가 아닙니다: {new_path}")
    
    try:
        # 디렉토리 변경
        old_directory = str(Path.cwd())
        os.chdir(new_path)
        new_current_directory = str(Path.cwd())
        
        return {
            "success": True,
            "message": "디렉토리가 성공적으로 변경되었습니다",
            "old_directory": old_directory,
            "new_directory": new_current_directory
        }
        
    except PermissionError:
        raise HTTPException(status_code=403, detail=f"디렉토리에 접근할 권한이 없습니다: {new_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"디렉토리 변경 중 오류가 발생했습니다: {str(e)}")


@router.post("/config/change-directory-and-list") 
async def change_directory_and_list(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    디렉토리를 변경하고 해당 디렉토리의 파일 목록을 반환합니다.
    """
    # 먼저 디렉토리 변경
    change_result = await change_directory(request, db)
    
    if change_result["success"]:
        # 변경된 디렉토리의 파일 목록 조회
        current_dir_info = await get_current_directory()
        
        return {
            **change_result,
            "contents": current_dir_info["contents"]
        }
    else:
        return change_result


@router.get("/config/extractors")
async def get_available_extractors(db: Session = Depends(get_db)):
    """
    사용 가능한 추출기 목록을 조회합니다.
    """
    from services.config_service import ConfigService
    
    default_extractors = ConfigService.get_json_config(
        db, "DEFAULT_EXTRACTORS", ["llm"]
    )
    
    # 추출기별 활성화 상태 확인
    extractor_config = ConfigService.get_extractor_config(db)
    
    available_extractors = []
    extractor_status = {
        "keybert": extractor_config.get("keybert_enabled", True),
        "ner": extractor_config.get("ner_enabled", True),
        "konlpy": extractor_config.get("konlpy_enabled", True),
        "llm": extractor_config.get("llm_enabled", False),
        "metadata": extractor_config.get("metadata_enabled", True),
        "langextract": extractor_config.get("langextract_enabled", False)
    }
    
    for extractor in ["keybert", "ner", "konlpy", "llm", "metadata", "langextract"]:
        if extractor_status.get(extractor, False):
            available_extractors.append(extractor)
    
    return {
        "default_extractors": default_extractors,
        "available_extractors": available_extractors,
        "extractor_status": extractor_status
    }
