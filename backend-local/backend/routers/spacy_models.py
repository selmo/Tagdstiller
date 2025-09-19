"""
spaCy 모델 관리 API
모델 조회, 다운로드, 테스트 등의 기능을 제공합니다.
"""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.spacy_model_service import SpaCyModelService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/spacy-models", tags=["spacy-models"])

class ModelDownloadRequest(BaseModel):
    model_name: str

class ModelTestRequest(BaseModel):
    model_name: str

class ModelDownloadResponse(BaseModel):
    success: bool
    message: str
    model_name: str

class ModelTestResponse(BaseModel):
    success: bool
    message: str
    model_name: str

@router.get("/available")
def get_available_models():
    """다운로드 가능한 모든 spaCy 모델 목록을 반환합니다."""
    try:
        models = SpaCyModelService.get_available_models()
        return {
            "models": models,
            "total_count": len(models)
        }
    except Exception as e:
        logger.error(f"사용 가능한 모델 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 목록 조회 실패: {str(e)}")

@router.get("/installed")
def get_installed_models():
    """설치된 spaCy 모델 목록을 반환합니다."""
    try:
        models = SpaCyModelService.get_installed_models()
        return {
            "models": models,
            "total_count": len(models)
        }
    except Exception as e:
        logger.error(f"설치된 모델 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"설치된 모델 조회 실패: {str(e)}")

@router.get("/info/{model_name}")
def get_model_info(model_name: str):
    """특정 모델의 상세 정보를 반환합니다."""
    try:
        model_info = SpaCyModelService.get_model_info(model_name)
        if model_info is None:
            raise HTTPException(status_code=404, detail=f"지원하지 않는 모델: {model_name}")
        
        return model_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"모델 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 정보 조회 실패: {str(e)}")

@router.post("/download", response_model=ModelDownloadResponse)
def download_model(request: ModelDownloadRequest, background_tasks: BackgroundTasks):
    """spaCy 모델을 다운로드합니다."""
    try:
        logger.info(f"모델 다운로드 요청: {request.model_name}")
        
        # 백그라운드에서 다운로드 실행
        success, message = SpaCyModelService.download_model(request.model_name)
        
        return ModelDownloadResponse(
            success=success,
            message=message,
            model_name=request.model_name
        )
    except Exception as e:
        logger.error(f"모델 다운로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 다운로드 실패: {str(e)}")

@router.post("/test", response_model=ModelTestResponse)
def test_model(request: ModelTestRequest):
    """모델이 정상적으로 작동하는지 테스트합니다."""
    try:
        logger.info(f"모델 테스트 요청: {request.model_name}")
        
        success, message = SpaCyModelService.test_model(request.model_name)
        
        return ModelTestResponse(
            success=success,
            message=message,
            model_name=request.model_name
        )
    except Exception as e:
        logger.error(f"모델 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=f"모델 테스트 실패: {str(e)}")

@router.get("/recommended")
def get_recommended_models():
    """권장 spaCy 모델 목록을 반환합니다."""
    try:
        all_models = SpaCyModelService.get_available_models()
        recommended_models = [model for model in all_models if model.get('recommended', False)]
        
        return {
            "models": recommended_models,
            "total_count": len(recommended_models)
        }
    except Exception as e:
        logger.error(f"권장 모델 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"권장 모델 조회 실패: {str(e)}")