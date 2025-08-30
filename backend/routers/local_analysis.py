"""
로컬 파일 분석 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from dependencies import get_db
from services.local_file_analyzer import LocalFileAnalyzer
from services.document_parser_service import DocumentParserService


# Request/Response 모델
class AnalyzeFileRequest(BaseModel):
    file_path: str
    extractors: Optional[List[str]] = None
    force_reanalyze: bool = False
    force_reparse: bool = False  # 파싱부터 다시 수행할지 여부


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


class DocumentParsingResponse(BaseModel):
    file_info: Dict[str, Any]
    parsing_timestamp: str
    parsers_used: List[str]
    parsing_results: Dict[str, Any]
    summary: Dict[str, Any]
    output_directory: str


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
        
        # 완전 파싱 수행
        results = parser_service.parse_document_comprehensive(
            file_path=file_path,
            force_reparse=request.force_reparse
        )
        
        return DocumentParsingResponse(
            file_info=results["file_info"],
            parsing_timestamp=results["parsing_timestamp"],
            parsers_used=results["parsers_used"],
            parsing_results=results["parsing_results"],
            summary=results["summary"],
            output_directory=str(parser_service.get_output_directory(file_path))
        )
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 중 오류가 발생했습니다: {str(e)}")


@router.get("/parse", response_model=DocumentParsingResponse)
async def parse_document_comprehensive_get(
    file_path: str = Query(..., description="파싱할 문서 경로"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 문서를 완전 파싱합니다.
    """
    request = ParseDocumentRequest(
        file_path=file_path,
        force_reparse=force_reparse
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
            
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path) or request.force_reparse:
            # 파싱 결과가 없거나 재파싱 요청시 완전 파싱 수행
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path,
                force_reparse=request.force_reparse
            )
        else:
            # 기존 파싱 결과 로드
            parsing_results = parser_service.load_existing_parsing_results(file_path)
        
        # 2. 파싱 결과를 기반으로 키워드 추출 분석 수행
        result = analyzer.analyze_file(
            file_path=str(file_path),
            extractors=request.extractors,
            force_reanalyze=request.force_reanalyze,
            parsing_results=parsing_results  # 파싱 결과 전달
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
        raise HTTPException(status_code=500, detail=f"분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/analyze", response_model=FileAnalysisResponse)
async def analyze_local_file_get(
    file_path: str = Query(..., description="분석할 파일 경로"),
    extractors: Optional[str] = Query(None, description="사용할 추출기 (쉼표로 구분)"),
    force_reanalyze: bool = Query(False, description="재분석 여부"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
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
        force_reparse=force_reparse
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
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path_obj) or force_reparse:
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path_obj,
                force_reparse=force_reparse
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path_obj)
        
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
            return {
                "file_info": parsing_results["file_info"],
                "parser_name": parser_name,
                "metadata": parser_result.get("metadata"),
                "parsing_timestamp": parsing_results.get("parsing_timestamp")
            }
        else:
            # 모든 파서의 메타데이터 반환
            all_metadata = {}
            for parser, result in parsing_results.get("parsing_results", {}).items():
                if result.get("success") and result.get("metadata"):
                    all_metadata[parser] = result["metadata"]
            
            return {
                "file_info": parsing_results["file_info"],
                "parsing_timestamp": parsing_results.get("parsing_timestamp"),
                "parsers_used": parsing_results.get("parsers_used", []),
                "metadata_by_parser": all_metadata,
                "summary": parsing_results.get("summary", {})
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
    
    return await get_file_metadata(file_path, force_reparse, parser_name, db)


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
    
    parser_service = DocumentParserService()
    
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
            
        # 파일 존재 여부 확인
        if not file_path_obj.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        # 구조 분석 결과 파일 경로
        output_dir = parser_service.get_output_directory(file_path_obj)
        structure_result_path = output_dir / "structure_analysis.json"
        
        # 기존 구조 분석 결과 확인
        if not force_reanalyze and structure_result_path.exists():
            with open(structure_result_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path_obj) or force_reparse:
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path_obj,
                force_reparse=force_reparse
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path_obj)
        
        # 2. 구조 분석 수행
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
        
        # 전체 요약 계산
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
        
        return structure_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"구조 분석 중 오류가 발생했습니다: {str(e)}")


@router.get("/structure-analysis")
async def get_structure_analysis(
    file_path: str = Query(..., description="구조 분석 결과를 조회할 파일 경로"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    force_reanalyze: bool = Query(False, description="재분석 여부"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 문서 구조 분석을 수행하거나 조회합니다.
    """
    request = {
        "file_path": file_path,
        "force_reparse": force_reparse,
        "force_reanalyze": force_reanalyze
    }
    
    return await analyze_document_structure(request, db)


@router.post("/knowledge-graph")
async def generate_knowledge_graph(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    문서로부터 Knowledge Graph를 생성합니다.
    
    - 파싱 및 키워드 추출 결과를 활용합니다
    - 엔티티와 관계를 추출하여 그래프 구조로 구성합니다
    - 결과는 파일로 저장되며 기본적으로 재사용됩니다
    """
    from pathlib import Path
    import json
    from services.kg_builder import KGBuilder
    
    file_path = request.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="파일 경로가 필요합니다")
    
    force_reparse = request.get("force_reparse", False)
    force_reanalyze = request.get("force_reanalyze", False)
    force_rebuild = request.get("force_rebuild", False)
    
    parser_service = DocumentParserService()
    analyzer = LocalFileAnalyzer(db)
    
    try:
        file_path_obj = Path(file_path)
        if not file_path_obj.is_absolute():
            file_path_obj = Path.cwd() / file_path_obj
            
        # 파일 존재 여부 확인
        if not file_path_obj.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {file_path}")
        
        # Knowledge Graph 결과 파일 경로
        output_dir = parser_service.get_output_directory(file_path_obj)
        kg_result_path = output_dir / "knowledge_graph.json"
        
        # 기존 KG 결과 확인
        if not force_rebuild and kg_result_path.exists():
            with open(kg_result_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 1. 파싱 결과 확인 및 필요시 파싱 수행
        if not parser_service.has_parsing_results(file_path_obj) or force_reparse:
            parsing_results = parser_service.parse_document_comprehensive(
                file_path=file_path_obj,
                force_reparse=force_reparse
            )
        else:
            parsing_results = parser_service.load_existing_parsing_results(file_path_obj)
        
        # 2. 키워드 추출 결과 확인 및 필요시 분석 수행
        analysis_result_path = file_path_obj.parent / f"{file_path_obj.name}.analysis.json"
        if not force_reanalyze and analysis_result_path.exists():
            with open(analysis_result_path, 'r', encoding='utf-8') as f:
                analysis_results = json.load(f)
        else:
            # 키워드 추출 수행
            result = analyzer.analyze_file(
                file_path=str(file_path_obj),
                extractors=None,  # 모든 추출기 사용
                force_reanalyze=force_reanalyze,
                parsing_results=parsing_results
            )
            analysis_results = result
        
        # 3. Knowledge Graph 생성
        kg_builder = KGBuilder(db)
        
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
        
        # KG 생성
        kg_result = kg_builder.build_knowledge_graph(
            file_path=str(file_path_obj),
            document_text=document_text,
            keywords=analysis_results.get("keywords", {}),
            metadata=parsing_results.get("file_info", {}),
            force_rebuild=force_rebuild
        )
        
        # 결과에 추가 정보 포함
        kg_with_context = {
            "file_info": parsing_results["file_info"],
            "generation_timestamp": datetime.now().isoformat(),
            "source_parser": best_parser,
            "keywords_used": len(analysis_results.get("keywords", {})),
            "knowledge_graph": kg_result,
            "statistics": {
                "total_entities": len(kg_result.get("entities", [])),
                "total_relationships": len(kg_result.get("relationships", [])),
                "entity_types": {}
            }
        }
        
        # 엔티티 타입별 통계
        entity_types = {}
        for entity in kg_result.get("entities", []):
            entity_type = entity.get("type", "unknown")
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        kg_with_context["statistics"]["entity_types"] = entity_types
        
        # 결과 저장
        output_dir.mkdir(exist_ok=True)
        with open(kg_result_path, 'w', encoding='utf-8') as f:
            json.dump(kg_with_context, f, ensure_ascii=False, indent=2)
        
        return kg_with_context
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Knowledge Graph 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/knowledge-graph")
async def get_knowledge_graph(
    file_path: str = Query(..., description="Knowledge Graph를 조회할 파일 경로"),
    force_reparse: bool = Query(False, description="재파싱 여부"),
    force_reanalyze: bool = Query(False, description="재분석 여부"),
    force_rebuild: bool = Query(False, description="KG 재생성 여부"),
    db: Session = Depends(get_db)
):
    """
    GET 방식으로 Knowledge Graph를 생성하거나 조회합니다.
    """
    request = {
        "file_path": file_path,
        "force_reparse": force_reparse,
        "force_reanalyze": force_reanalyze,
        "force_rebuild": force_rebuild
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
        db, "DEFAULT_EXTRACTORS", ["keybert", "ner", "konlpy", "metadata"]
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