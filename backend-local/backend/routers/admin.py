from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependencies import get_db
from services.config_cache import config_cache
from services.config_service import ConfigService

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/config/refresh")
def refresh_config_cache(db: Session = Depends(get_db)):
    """설정 캐시를 새로고침합니다."""
    try:
        config_cache.refresh_all(db)
        return {
            "message": "Config cache refreshed successfully",
            "cache_stats": config_cache.get_cache_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh cache: {str(e)}")

@router.post("/config/refresh/{key}")
def refresh_config_key(key: str, db: Session = Depends(get_db)):
    """특정 설정 키를 새로고침합니다."""
    try:
        config_cache.refresh_key(key, db)
        return {
            "message": f"Config key '{key}' refreshed successfully",
            "value": config_cache.get(key)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh key: {str(e)}")

@router.get("/config/cache/stats")
def get_cache_stats():
    """캐시 통계를 조회합니다."""
    return config_cache.get_cache_stats()

@router.get("/config/cache/all")
def get_all_cached_configs():
    """모든 캐시된 설정을 조회합니다."""
    return {
        "cached_configs": config_cache.get_all(),
        "stats": config_cache.get_cache_stats()
    }