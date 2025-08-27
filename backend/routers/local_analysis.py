"""
로컬 파일 분석 API 라우터
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from dependencies import get_db
from services.local_file_analyzer import LocalFileAnalyzer


# Request/Response 모델
class AnalyzeFileRequest(BaseModel):
    file_path: str
    extractors: Optional[List[str]] = None
    force_reanalyze: bool = False


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


router = APIRouter(prefix="/local-analysis", tags=["local-analysis"])


@router.post("/analyze", response_model=FileAnalysisResponse)
async def analyze_local_file(
    request: AnalyzeFileRequest,
    db: Session = Depends(get_db)
):
    """
    로컬 파일을 분석하여 키워드를 추출합니다.
    
    - **file_path**: 분석할 파일의 경로 (루트 디렉토리 기준 상대 경로 또는 절대 경로)
    - **extractors**: 사용할 추출기 목록 (기본값: 설정된 기본 추출기)
    - **force_reanalyze**: 기존 결과가 있어도 재분석할지 여부 (기본값: false)
    """
    analyzer = LocalFileAnalyzer(db)
    
    try:
        result = analyzer.analyze_file(
            file_path=request.file_path,
            extractors=request.extractors,
            force_reanalyze=request.force_reanalyze
        )
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
        force_reanalyze=force_reanalyze
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


@router.post("/reanalyze", response_model=FileAnalysisResponse)
async def reanalyze_local_file(
    request: AnalyzeFileRequest,
    db: Session = Depends(get_db)
):
    """
    파일을 재분석합니다. 기존 결과를 백업한 후 새로 분석합니다.
    """
    # force_reanalyze를 True로 설정
    request.force_reanalyze = True
    
    return await analyze_local_file(request, db)


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