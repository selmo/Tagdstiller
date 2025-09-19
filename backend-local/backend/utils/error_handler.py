"""
오류 처리 유틸리티 모듈

API 엔드포인트에서 발생하는 예외를 일관성 있게 처리하고 로깅하기 위한 헬퍼 함수들을 제공합니다.
"""

import logging
import traceback
from typing import Dict, Any, Optional
from fastapi import HTTPException


def log_and_raise_http_exception(
    e: Exception,
    operation: str,
    status_code: int = 500,
    context: Optional[Dict[str, Any]] = None,
    logger_name: Optional[str] = None
) -> None:
    """
    예외를 상세히 로깅하고 HTTPException으로 변환하여 발생시킵니다.
    
    Args:
        e: 발생한 예외
        operation: 수행 중이던 작업 (예: "Knowledge Graph 생성", "구조 분석")
        status_code: HTTP 상태 코드 (기본값: 500)
        context: 추가 컨텍스트 정보
        logger_name: 사용할 로거 이름 (기본값: 호출한 모듈)
    
    Raises:
        HTTPException: 상세한 오류 정보가 포함된 HTTP 예외
    """
    if logger_name:
        logger = logging.getLogger(logger_name)
    else:
        # 호출한 모듈의 이름을 자동으로 가져오기
        import inspect
        frame = inspect.currentframe().f_back
        logger = logging.getLogger(frame.f_globals.get('__name__', 'unknown'))
    
    # 상세한 오류 정보 수집
    error_details = {
        "error_type": type(e).__name__,
        "error_message": str(e),
        "operation": operation,
        "traceback": traceback.format_exc(),
        "context": context or {}
    }
    
    # 오류 정보 로깅
    logger.error(f"❌ {operation} 중 예외 발생:")
    logger.error(f"   - 작업: {error_details['operation']}")
    logger.error(f"   - 오류 타입: {error_details['error_type']}")  
    logger.error(f"   - 오류 메시지: {error_details['error_message']}")
    
    if context:
        logger.error(f"   - 컨텍스트: {context}")
    
    logger.error(f"   - 스택 트레이스:\n{error_details['traceback']}")
    
    # HTTPException 발생
    raise HTTPException(
        status_code=status_code, 
        detail=f"{operation} 중 오류가 발생했습니다: [{error_details['error_type']}] {error_details['error_message']}"
    )


def collect_context_info(local_vars: Dict[str, Any], keys: list = None) -> Dict[str, Any]:
    """
    로컬 변수들로부터 컨텍스트 정보를 안전하게 수집합니다.
    
    Args:
        local_vars: locals() 함수의 반환값
        keys: 수집할 변수명 목록 (None이면 기본 키들 사용)
    
    Returns:
        수집된 컨텍스트 정보 딕셔너리
    """
    if keys is None:
        keys = [
            "file_path", "use_llm", "force_rebuild", "force_reparse", "force_reanalyze",
            "best_parser", "parsing_results", "structure_results", "kg_result",
            "directory", "dataset_id"
        ]
    
    context_info = {}
    
    for key in keys:
        try:
            if key in local_vars:
                value = local_vars[key]
                # 복잡한 객체는 간단한 정보만 수집
                if key in ["parsing_results", "structure_results", "kg_result"]:
                    context_info[f"{key}_available"] = bool(value)
                    if isinstance(value, dict):
                        context_info[f"{key}_keys"] = list(value.keys())
                elif key == "file_path":
                    context_info[key] = str(value) if value else "unknown"
                else:
                    context_info[key] = value
            else:
                context_info[key] = "not_available"
        except Exception:
            context_info[key] = "collection_failed"
    
    return context_info


def safe_str_conversion(obj: Any, max_length: int = 200) -> str:
    """
    객체를 안전하게 문자열로 변환합니다.
    
    Args:
        obj: 변환할 객체
        max_length: 최대 문자열 길이
    
    Returns:
        변환된 문자열 (필요시 잘림)
    """
    try:
        if obj is None:
            return "None"
        
        str_obj = str(obj)
        if len(str_obj) > max_length:
            return str_obj[:max_length] + "... (truncated)"
        return str_obj
    except Exception:
        return f"<{type(obj).__name__}: string conversion failed>"


class APIErrorHandler:
    """
    API 엔드포인트에서 사용할 수 있는 컨텍스트 매니저 스타일의 오류 처리기
    """
    
    def __init__(self, operation: str, logger_name: Optional[str] = None):
        self.operation = operation
        self.logger_name = logger_name
        self.context = {}
    
    def add_context(self, **kwargs):
        """컨텍스트 정보 추가"""
        self.context.update(kwargs)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and exc_type != HTTPException:
            # HTTPException이 아닌 예외만 처리
            log_and_raise_http_exception(
                exc_val, 
                self.operation, 
                context=self.context,
                logger_name=self.logger_name
            )
        return False  # 예외를 재발생시킴


# 데코레이터 스타일 오류 처리
def handle_api_errors(operation: str, logger_name: Optional[str] = None):
    """
    API 함수를 감싸서 자동으로 오류 처리를 수행하는 데코레이터
    
    사용 예:
    @handle_api_errors("파일 분석")
    async def analyze_file(...):
        ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                # locals()에서 컨텍스트 수집은 데코레이터에서는 제한적
                context = {"args_count": len(args), "kwargs_keys": list(kwargs.keys())}
                log_and_raise_http_exception(
                    e, operation, context=context, logger_name=logger_name
                )
        return wrapper
    return decorator