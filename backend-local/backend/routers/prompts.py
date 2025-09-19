"""
프롬프트 템플릿 관리 API

이 모듈은 LLM 프롬프트 템플릿의 조회, 수정, 추가를 위한 API 엔드포인트를 제공합니다.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from dependencies import get_db
from prompts.templates import list_available_templates
from prompts.config import (
    get_available_templates_with_info, 
    save_custom_template_to_config,
    load_custom_templates_from_config
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/prompts", tags=["prompts"])


class TemplateInfo(BaseModel):
    """템플릿 정보 모델"""
    description: str
    required_variables: List[str]
    default_variables: Dict[str, Any]
    preview: str


class CustomTemplateRequest(BaseModel):
    """커스텀 템플릿 생성 요청 모델"""
    category: str
    name: str
    template: str
    variables: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class TemplateTestRequest(BaseModel):
    """템플릿 테스트 요청 모델"""
    category: str
    template_name: str
    test_variables: Dict[str, Any]


@router.get("/templates", response_model=Dict[str, Dict[str, TemplateInfo]])
def get_available_templates(db: Session = Depends(get_db)):
    """사용 가능한 모든 프롬프트 템플릿 목록 조회"""
    try:
        # 커스텀 템플릿 로드
        load_custom_templates_from_config(db)
        
        # 템플릿 정보 가져오기
        templates_info = get_available_templates_with_info()
        
        logger.info(f"📋 프롬프트 템플릿 목록 조회 - {sum(len(templates) for templates in templates_info.values())}개 템플릿")
        
        return templates_info
    except Exception as e:
        logger.error(f"❌ 템플릿 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{category}")
def get_templates_by_category(category: str, db: Session = Depends(get_db)):
    """특정 카테고리의 템플릿 목록 조회"""
    try:
        load_custom_templates_from_config(db)
        templates_info = get_available_templates_with_info()
        
        if category not in templates_info:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        logger.info(f"📋 카테고리 '{category}' 템플릿 조회 - {len(templates_info[category])}개")
        
        return templates_info[category]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 카테고리 템플릿 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{category}/{template_name}")
def get_template_details(category: str, template_name: str, db: Session = Depends(get_db)):
    """특정 템플릿의 상세 정보 조회"""
    try:
        load_custom_templates_from_config(db)
        templates_info = get_available_templates_with_info()
        
        if category not in templates_info:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        if template_name not in templates_info[category]:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found in category '{category}'")
        
        logger.info(f"📄 템플릿 상세 조회: {category}.{template_name}")
        
        return templates_info[category][template_name]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 템플릿 상세 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/custom")
def create_custom_template(request: CustomTemplateRequest, db: Session = Depends(get_db)):
    """커스텀 프롬프트 템플릿 생성"""
    try:
        # 템플릿 저장
        success = save_custom_template_to_config(
            db, 
            request.category, 
            request.name, 
            request.template, 
            request.variables
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save custom template")
        
        logger.info(f"✅ 커스텀 템플릿 생성: {request.category}.{request.name}")
        
        return {
            "message": "Custom template created successfully",
            "category": request.category,
            "name": request.name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 커스텀 템플릿 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/templates/test")
def test_template(request: TemplateTestRequest, db: Session = Depends(get_db)):
    """프롬프트 템플릿 테스트"""
    try:
        from prompts.templates import get_prompt_template
        
        # 커스텀 템플릿 로드
        load_custom_templates_from_config(db)
        
        # 템플릿으로 프롬프트 생성
        prompt = get_prompt_template(
            request.category, 
            request.template_name, 
            **request.test_variables
        )
        
        logger.info(f"🧪 템플릿 테스트: {request.category}.{request.template_name}")
        
        return {
            "generated_prompt": prompt,
            "character_count": len(prompt),
            "word_count": len(prompt.split()),
            "variables_used": request.test_variables
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ 템플릿 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
def get_template_categories():
    """프롬프트 템플릿 카테고리 목록 조회"""
    try:
        templates = list_available_templates()
        categories = list(templates.keys())
        
        category_info = {
            'keyword_extraction': {
                'name': '키워드 추출',
                'description': '문서에서 중요한 키워드를 추출하는 프롬프트',
                'template_count': len(templates.get('keyword_extraction', {}))
            },
            'document_summary': {
                'name': '문서 요약',
                'description': '문서의 내용을 요약하는 프롬프트',
                'template_count': len(templates.get('document_summary', {}))
            },
            'metadata_extraction': {
                'name': '메타데이터 추출',
                'description': '문서의 메타데이터를 추출하는 프롬프트',
                'template_count': len(templates.get('metadata_extraction', {}))
            }
        }
        
        logger.info(f"📂 템플릿 카테고리 조회 - {len(categories)}개 카테고리")
        
        return {
            'categories': categories,
            'category_info': category_info,
            'total_categories': len(categories),
            'total_templates': sum(len(templates) for templates in templates.values())
        }
    except Exception as e:
        logger.error(f"❌ 카테고리 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variables/{category}")
def get_template_variables(category: str):
    """특정 카테고리에서 사용하는 변수 목록 조회"""
    try:
        from prompts.config import PromptConfig
        
        # 기본 설정에서 변수 정보 추출
        config = PromptConfig()
        
        category_variables = {
            'keyword_extraction': {
                'required': ['text', 'max_keywords'],
                'optional': ['language', 'domain'],
                'description': {
                    'text': '키워드를 추출할 텍스트 내용',
                    'max_keywords': '추출할 최대 키워드 개수',
                    'language': '텍스트 언어 (ko, en, auto)',
                    'domain': '문서 도메인 (general, academic, technical)'
                }
            },
            'document_summary': {
                'required': ['text'],
                'optional': ['language', 'domain'],
                'description': {
                    'text': '요약할 문서 텍스트 내용',
                    'language': '텍스트 언어 (ko, en, auto)',
                    'domain': '문서 도메인 (general, academic, technical)'
                }
            },
            'metadata_extraction': {
                'required': ['text'],
                'optional': ['language'],
                'description': {
                    'text': '메타데이터를 추출할 문서 텍스트',
                    'language': '텍스트 언어 (ko, en)'
                }
            }
        }
        
        if category not in category_variables:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        logger.info(f"📝 카테고리 '{category}' 변수 정보 조회")
        
        return category_variables[category]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 템플릿 변수 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))