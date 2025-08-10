import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Iterator
import json
import time
import threading
import sys
from db.models import Config
from response_models import ConfigCreate, ConfigUpdate, ConfigResponse
from dependencies import get_db

logger = logging.getLogger(__name__)

# Global dictionary to track download progress
download_progress = {}

router = APIRouter(prefix="/configs", tags=["configs"])

@router.get("/", response_model=List[ConfigResponse])
def list_configs(db: Session = Depends(get_db)):
    """Get all configuration key-value pairs."""
    configs = db.query(Config).all()
    return configs

@router.get("/{key}", response_model=ConfigResponse)
def get_config(key: str, db: Session = Depends(get_db)):
    """Get a specific configuration value by key."""
    config = db.query(Config).filter(Config.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    return config

@router.put("/{key}", response_model=ConfigResponse)
def update_config(key: str, config_data: ConfigUpdate, db: Session = Depends(get_db)):
    """Update or create a configuration value."""
    config = db.query(Config).filter(Config.key == key).first()
    
    if config:
        # Update existing config
        config.value = config_data.value
        if config_data.description is not None:
            config.description = config_data.description
        # updated_at will be automatically set by onupdate
    else:
        # Create new config
        config = Config(
            key=key,
            value=config_data.value,
            description=config_data.description
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    return config

@router.post("/", response_model=ConfigResponse)
def create_config(config_data: ConfigCreate, db: Session = Depends(get_db)):
    """Create a new configuration entry."""
    # Check if key already exists
    existing_config = db.query(Config).filter(Config.key == config_data.key).first()
    if existing_config:
        raise HTTPException(status_code=400, detail=f"Config key '{config_data.key}' already exists")
    
    config = Config(
        key=config_data.key,
        value=config_data.value,
        description=config_data.description
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

@router.delete("/{key}")
def delete_config(key: str, db: Session = Depends(get_db)):
    """Delete a configuration entry."""
    config = db.query(Config).filter(Config.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    
    db.delete(config)
    db.commit()
    return {"message": f"Config key '{key}' deleted successfully"}

@router.get("/keybert/models")
def get_keybert_models() -> Dict[str, Any]:
    """Get available KeyBERT models for selection."""
    
    # Popular sentence transformer models for KeyBERT
    models = {
        "multilingual": [
            {
                "name": "all-MiniLM-L6-v2",
                "description": "Fast and efficient multilingual model (384 dimensions)",
                "size": "Small (~90MB)",
                "languages": ["English", "Korean", "Chinese", "Japanese", "and 100+ more"],
                "speed": "Fast",
                "quality": "Good",
                "recommended": True
            },
            {
                "name": "paraphrase-multilingual-MiniLM-L12-v2", 
                "description": "Multilingual paraphrase model (384 dimensions)",
                "size": "Medium (~420MB)",
                "languages": ["50+ languages including Korean"],
                "speed": "Medium",
                "quality": "Very Good"
            },
            {
                "name": "paraphrase-multilingual-mpnet-base-v2",
                "description": "High-quality multilingual model (768 dimensions)",
                "size": "Large (~1.1GB)",
                "languages": ["50+ languages including Korean"],
                "speed": "Slow",
                "quality": "Excellent"
            },
            {
                "name": "distiluse-base-multilingual-cased",
                "description": "Multilingual DistilUSE model (512 dimensions)",
                "size": "Medium (~500MB)",
                "languages": ["15 languages including Korean"],
                "speed": "Fast",
                "quality": "Good"
            },
            {
                "name": "sentence-transformers/LaBSE",
                "description": "Language-agnostic BERT Sentence Embedding",
                "size": "Large (~1.9GB)",
                "languages": ["109+ languages including Korean"],
                "speed": "Slow",
                "quality": "Excellent"
            }
        ],
        "korean_optimized": [
            {
                "name": "jhgan/ko-sroberta-multitask",
                "description": "Korean-optimized SBERT model",
                "size": "Medium (~400MB)",
                "languages": ["Korean", "English"],
                "speed": "Medium",
                "quality": "Excellent for Korean",
                "recommended": True
            },
            {
                "name": "jhgan/ko-sbert-nli",
                "description": "Korean SBERT for semantic similarity",
                "size": "Medium (~400MB)",
                "languages": ["Korean"],
                "speed": "Medium", 
                "quality": "Very Good for Korean"
            },
            {
                "name": "BM-K/KoSimCSE-roberta-multitask",
                "description": "Korean SimCSE model for semantic similarity",
                "size": "Medium (~420MB)",
                "languages": ["Korean"],
                "speed": "Medium",
                "quality": "Excellent for Korean"
            },
            {
                "name": "snunlp/KR-SBERT-V40K-klueNLI-augSTS",
                "description": "Korean SBERT trained on KLUE NLI and augmented STS",
                "size": "Medium (~400MB)",
                "languages": ["Korean"],
                "speed": "Medium",
                "quality": "Very Good for Korean"
            }
        ],
        "english_only": [
            {
                "name": "all-mpnet-base-v2",
                "description": "High-performance English model (768 dimensions)",
                "size": "Large (~420MB)",
                "languages": ["English"],
                "speed": "Medium",
                "quality": "Excellent"
            },
            {
                "name": "all-distilroberta-v1",
                "description": "Fast English model based on DistilRoBERTa",
                "size": "Medium (~290MB)",
                "languages": ["English"],
                "speed": "Fast",
                "quality": "Good"
            },
            {
                "name": "all-roberta-large-v1",
                "description": "Large RoBERTa model for high accuracy",
                "size": "Large (~1.4GB)",
                "languages": ["English"],
                "speed": "Slow",
                "quality": "Excellent"
            },
            {
                "name": "paraphrase-albert-small-v2",
                "description": "Small ALBERT model for paraphrase detection",
                "size": "Small (~40MB)",
                "languages": ["English"],
                "speed": "Very Fast",
                "quality": "Good"
            },
            {
                "name": "msmarco-distilbert-base-v4",
                "description": "DistilBERT trained on MS MARCO dataset",
                "size": "Medium (~260MB)",
                "languages": ["English"],
                "speed": "Fast",
                "quality": "Very Good"
            }
        ]
    }
    
    return {
        "models": models,
        "current_model": "all-MiniLM-L6-v2",  # Default model
        "recommendation": "For Korean documents, use 'jhgan/ko-sroberta-multitask'. For multilingual use, 'all-MiniLM-L6-v2' is recommended for speed, or 'paraphrase-multilingual-mpnet-base-v2' for quality."
    }

@router.get("/keybert/models/download/progress/{progress_key}")
def get_download_progress_stream(progress_key: str):
    """모델 다운로드 진행률을 스트리밍합니다."""
    
    def generate_progress() -> Iterator[str]:
        max_wait_time = 300  # 5분 최대 대기
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            if progress_key in download_progress:
                progress_data = download_progress[progress_key]
                
                # 서버 로그에 진행률 기록
                if progress_data["progress"] % 10 == 0 or progress_data["status"] in ["completed", "error"]:
                    logger.info(f"📊 다운로드 진행률 - {progress_data['model_name']}: {progress_data['progress']}% ({progress_data['message']})")
                
                # SSE 형식으로 데이터 전송
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # 완료되거나 오류가 발생하면 종료
                if progress_data["status"] in ["completed", "error"]:
                    break
                    
            else:
                # 진행률 데이터가 없으면 종료
                yield f"data: {json.dumps({'status': 'not_found', 'message': '진행률 정보를 찾을 수 없습니다'})}\n\n"
                break
            
            time.sleep(0.5)  # 0.5초마다 업데이트
        
        # 타임아웃 시
        if time.time() - start_time >= max_wait_time:
            yield f"data: {json.dumps({'status': 'timeout', 'message': '타임아웃이 발생했습니다'})}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.post("/keybert/models/{model_name}/download")
def download_keybert_model(model_name: str) -> Dict[str, Any]:
    """KeyBERT 모델을 다운로드하고 로드합니다."""
    logger.info(f"🔄 KeyBERT 모델 다운로드 요청: {model_name}")
    
    # 진행률 초기화
    progress_key = f"keybert_download_{model_name}"
    download_progress[progress_key] = {
        "status": "starting",
        "progress": 0,
        "message": "다운로드 준비 중...",
        "model_name": model_name,
        "start_time": time.time()
    }
    
    try:
        from sentence_transformers import SentenceTransformer
        import os
        from pathlib import Path
        
        # 현재 캐시 상태 확인 (새로운 huggingface hub 캐시 위치)
        cache_dirs = [
            Path.home() / ".cache" / "huggingface" / "hub",  # 새 위치
            Path.home() / ".cache" / "torch" / "sentence_transformers"  # 기존 위치 (fallback)
        ]
        was_cached = False
        
        download_progress[progress_key].update({
            "status": "checking_cache",
            "progress": 10,
            "message": "캐시 상태 확인 중..."
        })
        logger.info(f"📦 모델 '{model_name}' 캐시 상태 확인 중...")
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    if item.is_dir():
                        # 모델 이름이 포함된 폴더인지 확인 (더 정확한 매칭)
                        folder_name = item.name.lower()
                        model_name_for_hub = f"models--sentence-transformers--{model_name.replace('/', '--')}"
                        model_name_variations = [
                            model_name.lower(),
                            model_name.lower().replace("/", "_"),
                            model_name.lower().replace("-", "_"),
                            model_name.lower().replace("/", "__"),
                            model_name_for_hub.lower(),  # huggingface hub 형식
                        ]
                        
                        # 정확히 일치하거나 포함되어 있는지 확인
                        for variation in model_name_variations:
                            if variation in folder_name or folder_name in variation:
                                was_cached = True
                                logger.info(f"📦 모델 '{model_name}'이 이미 캐시되어 있음 (폴더: {item.name})")
                                break
                        
                        if was_cached:
                            break
            
            if was_cached:
                break
        
        # 모델 다운로드 시작 시간 기록
        start_time = time.time()
        
        if was_cached:
            download_progress[progress_key].update({
                "status": "loading_cached",
                "progress": 30,
                "message": "캐시된 모델 로드 중..."
            })
            logger.info(f"🔄 KeyBERT 모델 '{model_name}' 캐시에서 로드 중...")
        else:
            download_progress[progress_key].update({
                "status": "downloading",
                "progress": 20,
                "message": "모델 다운로드 중... (시간이 걸릴 수 있습니다)"
            })
            logger.info(f"📥 KeyBERT 모델 '{model_name}' 다운로드 시작...")
        
        # 진행률 업데이트 (다운로드/로드 중)
        download_progress[progress_key].update({
            "progress": 50,
            "message": "모델 초기화 중..."
        })
        
        # 모델 다운로드 및 로드 (자동으로 캐시됨)
        model = SentenceTransformer(model_name)
        
        # 완료 시간 기록
        process_time = time.time() - start_time
        
        download_progress[progress_key].update({
            "status": "validating",
            "progress": 80,
            "message": "모델 검증 중..."
        })
        
        if was_cached:
            logger.info(f"✅ KeyBERT 모델 '{model_name}' 캐시에서 로드 완료 (소요시간: {process_time:.2f}초)")
        else:
            logger.info(f"✅ KeyBERT 모델 '{model_name}' 다운로드 및 로드 완료 (소요시간: {process_time:.2f}초)")
        
        # 간단한 테스트로 모델 검증
        test_text = "테스트 문장입니다"
        embeddings = model.encode([test_text])
        embedding_dim = embeddings.shape[1] if len(embeddings.shape) > 1 else embeddings.shape[0]
        logger.info(f"🧪 모델 검증 완료 - 임베딩 차원: {embedding_dim}, 형태: {embeddings.shape}")
        
        download_progress[progress_key].update({
            "progress": 90,
            "message": "캐시 크기 계산 중..."
        })
        
        # 다운로드 후 캐시 크기 확인
        total_cache_size = 0
        cache_paths = []
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    if item.is_dir():
                        folder_name = item.name.lower()
                        model_name_for_hub = f"models--sentence-transformers--{model_name.replace('/', '--')}"
                        model_name_variations = [
                            model_name.lower(),
                            model_name.lower().replace("/", "_"),
                            model_name.lower().replace("-", "_"),
                            model_name.lower().replace("/", "__"),
                            model_name_for_hub.lower(),  # huggingface hub 형식
                        ]
                        
                        for variation in model_name_variations:
                            if variation in folder_name or folder_name in variation:
                                cache_paths.append(str(item))
                                folder_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                                total_cache_size += folder_size
                                break
        
        cache_size_mb = round(total_cache_size / (1024*1024), 2)
        logger.info(f"💾 모델 '{model_name}' 캐시 크기: {cache_size_mb}MB")
        
        # 진행률 완료
        download_progress[progress_key].update({
            "status": "completed",
            "progress": 100,
            "message": f"완료! (소요시간: {process_time:.1f}초, 크기: {cache_size_mb}MB)"
        })
        
        # 3초 후 진행률 데이터 정리
        def cleanup_progress():
            time.sleep(3)
            if progress_key in download_progress:
                del download_progress[progress_key]
        
        threading.Thread(target=cleanup_progress, daemon=True).start()
        
        return {
            "status": "success",
            "message": f"모델 '{model_name}'이 성공적으로 {'로드' if was_cached else '다운로드'}되었습니다",
            "model_name": model_name,
            "download_time_seconds": round(process_time, 2),
            "embedding_dimension": embedding_dim,
            "model_size_mb": cache_size_mb,
            "was_cached": was_cached,
            "cache_paths": cache_paths,
            "action": "loaded" if was_cached else "downloaded",
            "progress_key": progress_key
        }
        
    except Exception as e:
        error_msg = f"모델 '{model_name}' {'로드' if 'cached' in str(e).lower() else '다운로드'} 실패: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        # 진행률 오류 상태로 업데이트
        download_progress[progress_key].update({
            "status": "error",
            "progress": 0,
            "message": f"오류: {str(e)}"
        })
        
        return {
            "status": "error",
            "message": error_msg,
            "model_name": model_name,
            "error": str(e),
            "progress_key": progress_key
        }

@router.delete("/keybert/models/{model_name}/cache")
def delete_keybert_model_cache(model_name: str) -> Dict[str, Any]:
    """KeyBERT 모델 캐시를 삭제합니다."""
    logger.info(f"🗑️ KeyBERT 모델 캐시 삭제 요청: {model_name}")
    
    try:
        import os
        import shutil
        from pathlib import Path
        
        # sentence-transformers 캐시 디렉토리 찾기 (새로운 huggingface hub 캐시 위치)
        cache_dirs = [
            Path.home() / ".cache" / "huggingface" / "hub",  # 새 위치
            Path.home() / ".cache" / "torch" / "sentence_transformers"  # 기존 위치 (fallback)
        ]
        
        deleted_paths = []
        total_size_deleted = 0
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                # 모델 이름으로 시작하는 캐시 폴더들 찾기
                model_folders = []
                for item in cache_dir.iterdir():
                    if item.is_dir():
                        # 모델 이름이 포함된 폴더인지 확인 (더 정확한 매칭)
                        folder_name = item.name.lower()
                        model_name_for_hub = f"models--sentence-transformers--{model_name.replace('/', '--')}"
                        model_name_variations = [
                            model_name.lower(),
                            model_name.lower().replace("/", "_"),
                            model_name.lower().replace("-", "_"),
                            model_name.lower().replace("/", "__"),
                            model_name_for_hub.lower(),  # huggingface hub 형식
                        ]
                        
                        # 정확히 일치하거나 포함되어 있는지 확인
                        for variation in model_name_variations:
                            if variation in folder_name or folder_name in variation:
                                model_folders.append(item)
                                break
            
            # 찾은 폴더들 삭제
            for folder in model_folders:
                try:
                    # 폴더 크기 계산
                    folder_size = sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())
                    
                    # 폴더 삭제
                    shutil.rmtree(folder)
                    deleted_paths.append(str(folder))
                    total_size_deleted += folder_size
                    logger.info(f"🗑️ 삭제된 캐시 폴더: {folder} ({folder_size / (1024*1024):.2f}MB)")
                    
                except Exception as folder_error:
                    logger.warning(f"⚠️ 폴더 삭제 실패: {folder} - {folder_error}")
        
        if deleted_paths:
            logger.info(f"✅ KeyBERT 모델 '{model_name}' 캐시 삭제 완료 - 총 {len(deleted_paths)}개 폴더, {total_size_deleted / (1024*1024):.2f}MB")
            return {
                "status": "success",
                "message": f"모델 '{model_name}' 캐시가 성공적으로 삭제되었습니다",
                "model_name": model_name,
                "deleted_paths": deleted_paths,
                "total_size_mb": round(total_size_deleted / (1024*1024), 2)
            }
        else:
            logger.info(f"ℹ️ KeyBERT 모델 '{model_name}' 캐시를 찾을 수 없음")
            return {
                "status": "success",
                "message": f"모델 '{model_name}'의 캐시를 찾을 수 없습니다 (이미 삭제되었거나 다운로드되지 않음)",
                "model_name": model_name,
                "deleted_paths": [],
                "total_size_mb": 0
            }
            
    except Exception as e:
        error_msg = f"모델 '{model_name}' 캐시 삭제 실패: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "model_name": model_name,
            "error": str(e)
        }

@router.get("/keybert/models/{model_name}/status")
def get_keybert_model_status(model_name: str) -> Dict[str, Any]:
    """KeyBERT 모델의 캐시 상태를 확인합니다."""
    try:
        import os
        from pathlib import Path
        
        # sentence-transformers 캐시 디렉토리 확인 (새로운 huggingface hub 캐시 위치)
        cache_dirs = [
            Path.home() / ".cache" / "huggingface" / "hub",  # 새 위치
            Path.home() / ".cache" / "torch" / "sentence_transformers"  # 기존 위치 (fallback)
        ]
        
        is_cached = False
        cache_paths = []
        total_size = 0
        
        for cache_dir in cache_dirs:
            if cache_dir.exists():
                # 모델 이름으로 시작하는 캐시 폴더들 찾기
                for item in cache_dir.iterdir():
                    if item.is_dir():
                        folder_name = item.name.lower()
                        model_name_for_hub = f"models--sentence-transformers--{model_name.replace('/', '--')}"
                        model_name_variations = [
                            model_name.lower(),
                            model_name.lower().replace("/", "_"),
                            model_name.lower().replace("-", "_"),
                            model_name.lower().replace("/", "__"),
                            model_name_for_hub.lower(),  # huggingface hub 형식
                        ]
                        
                        # 정확히 일치하거나 포함되어 있는지 확인
                        for variation in model_name_variations:
                            if variation in folder_name or folder_name in variation:
                                is_cached = True
                                cache_paths.append(str(item))
                                # 폴더 크기 계산
                                folder_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                                total_size += folder_size
                                break
        
        return {
            "status": "success",
            "model_name": model_name,
            "is_cached": is_cached,
            "cache_paths": cache_paths,
            "total_size_mb": round(total_size / (1024*1024), 2) if total_size > 0 else 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"모델 상태 확인 실패: {str(e)}",
            "model_name": model_name,
            "error": str(e)
        }

@router.get("/spacy/models")
def get_spacy_models() -> Dict[str, Any]:
    """사용 가능한 spaCy NER 모델 목록을 가져옵니다."""
    
    # spaCy NER 모델 목록
    models = {
        "korean": [
            {
                "name": "ko_core_news_sm",
                "description": "한국어 소형 모델 (12MB)",
                "size": "Small (~12MB)",
                "languages": ["Korean"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식"],
                "speed": "빠름",
                "accuracy": "좋음",
                "recommended": True
            },
            {
                "name": "ko_core_news_md",
                "description": "한국어 중형 모델 (40MB)",
                "size": "Medium (~40MB)",
                "languages": ["Korean"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식", "단어 벡터"],
                "speed": "보통",
                "accuracy": "매우 좋음"
            },
            {
                "name": "ko_core_news_lg",
                "description": "한국어 대형 모델 (560MB)",
                "size": "Large (~560MB)",
                "languages": ["Korean"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식", "단어 벡터"],
                "speed": "느림",
                "accuracy": "우수"
            }
        ],
        "english": [
            {
                "name": "en_core_web_sm",
                "description": "영어 소형 모델 (12MB)",
                "size": "Small (~12MB)",
                "languages": ["English"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식", "의존성 파싱"],
                "speed": "빠름",
                "accuracy": "좋음"
            },
            {
                "name": "en_core_web_md",
                "description": "영어 중형 모델 (40MB)",
                "size": "Medium (~40MB)",
                "languages": ["English"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식", "의존성 파싱", "단어 벡터"],
                "speed": "보통",
                "accuracy": "매우 좋음"
            },
            {
                "name": "en_core_web_lg",
                "description": "영어 대형 모델 (560MB)",
                "size": "Large (~560MB)",
                "languages": ["English"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식", "의존성 파싱", "단어 벡터"],
                "speed": "느림",
                "accuracy": "우수"
            },
            {
                "name": "en_core_web_trf",
                "description": "영어 Transformer 모델 (400MB)",
                "size": "Large (~400MB)",
                "languages": ["English"],
                "capabilities": ["토큰화", "품사 태깅", "개체명 인식", "의존성 파싱", "Transformer"],
                "speed": "매우 느림",
                "accuracy": "최고"
            }
        ],
        "multilingual": [
            {
                "name": "xx_ent_wiki_sm",
                "description": "다국어 개체명 인식 모델 (12MB)",
                "size": "Small (~12MB)",
                "languages": ["Multi-language"],
                "capabilities": ["개체명 인식"],
                "speed": "빠름",
                "accuracy": "좋음"
            }
        ]
    }
    
    return {
        "models": models,
        "current_model": "ko_core_news_sm",  # Default model
        "recommendation": "한국어 문서는 'ko_core_news_sm', 영어 문서는 'en_core_web_sm' 사용을 권장합니다."
    }

@router.post("/spacy/models/{model_name}/download")
def download_spacy_model(model_name: str) -> Dict[str, Any]:
    """spaCy 모델을 다운로드합니다."""
    logger.info(f"🔄 spaCy 모델 다운로드 요청: {model_name}")
    
    # 진행률 초기화
    progress_key = f"spacy_download_{model_name}"
    download_progress[progress_key] = {
        "status": "starting",
        "progress": 0,
        "message": "다운로드 준비 중...",
        "model_name": model_name,
        "start_time": time.time()
    }
    
    try:
        import subprocess
        import spacy
        from pathlib import Path
        
        # 모델이 이미 설치되어 있는지 확인
        download_progress[progress_key].update({
            "status": "checking",
            "progress": 10,
            "message": "설치된 모델 확인 중..."
        })
        
        try:
            # 모델 로드 시도
            nlp = spacy.load(model_name)
            
            download_progress[progress_key].update({
                "status": "completed",
                "progress": 100,
                "message": "모델이 이미 설치되어 있습니다"
            })
            
            logger.info(f"✅ spaCy 모델 '{model_name}'이 이미 설치되어 있음")
            
            # 모델 정보 가져오기
            model_info = {
                "lang": nlp.lang,
                "pipeline": nlp.pipe_names,
                "version": getattr(nlp.meta, 'version', 'unknown')
            }
            
            return {
                "status": "success",
                "message": f"모델 '{model_name}'이 이미 설치되어 있습니다",
                "model_name": model_name,
                "already_installed": True,
                "model_info": model_info,
                "progress_key": progress_key
            }
            
        except OSError:
            # 모델이 없으므로 다운로드 진행
            logger.info(f"📥 spaCy 모델 '{model_name}' 다운로드 시작...")
            
            download_progress[progress_key].update({
                "status": "downloading",
                "progress": 30,
                "message": "모델 다운로드 중... (시간이 걸릴 수 있습니다)"
            })
            
            # spaCy 다운로드 명령 실행
            cmd = [sys.executable, "-m", "spacy", "download", model_name]
            
            # 프로세스 실행
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # 진행률 업데이트 시뮬레이션
            import threading
            def update_progress():
                progress_steps = [
                    (40, "패키지 정보 확인 중..."),
                    (50, "모델 파일 다운로드 중..."),
                    (70, "모델 설치 중..."),
                    (90, "설치 마무리 중...")
                ]
                
                for progress, message in progress_steps:
                    time.sleep(2)
                    if progress_key in download_progress:
                        download_progress[progress_key].update({
                            "progress": progress,
                            "message": message
                        })
            
            progress_thread = threading.Thread(target=update_progress)
            progress_thread.start()
            
            # 프로세스 완료 대기
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                # 다운로드 성공
                download_progress[progress_key].update({
                    "status": "validating",
                    "progress": 95,
                    "message": "모델 검증 중..."
                })
                
                # 모델 로드 테스트
                nlp = spacy.load(model_name)
                
                download_progress[progress_key].update({
                    "status": "completed",
                    "progress": 100,
                    "message": "다운로드 완료!"
                })
                
                logger.info(f"✅ spaCy 모델 '{model_name}' 다운로드 및 설치 완료")
                
                # 모델 정보
                model_info = {
                    "lang": nlp.lang,
                    "pipeline": nlp.pipe_names,
                    "version": getattr(nlp.meta, 'version', 'unknown')
                }
                
                # 5초 후 진행률 데이터 정리
                def cleanup_progress():
                    time.sleep(5)
                    if progress_key in download_progress:
                        del download_progress[progress_key]
                
                threading.Thread(target=cleanup_progress, daemon=True).start()
                
                return {
                    "status": "success",
                    "message": f"모델 '{model_name}'이 성공적으로 다운로드되었습니다",
                    "model_name": model_name,
                    "model_info": model_info,
                    "progress_key": progress_key
                }
            else:
                # 다운로드 실패
                error_msg = stderr if stderr else "알 수 없는 오류"
                download_progress[progress_key].update({
                    "status": "error",
                    "progress": 0,
                    "message": f"다운로드 실패: {error_msg}"
                })
                
                logger.error(f"❌ spaCy 모델 '{model_name}' 다운로드 실패: {error_msg}")
                
                return {
                    "status": "error",
                    "message": f"모델 다운로드 실패: {error_msg}",
                    "model_name": model_name,
                    "error": error_msg,
                    "progress_key": progress_key
                }
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ spaCy 모델 처리 중 오류: {error_msg}")
        
        download_progress[progress_key].update({
            "status": "error",
            "progress": 0,
            "message": f"오류: {error_msg}"
        })
        
        return {
            "status": "error",
            "message": f"모델 처리 중 오류: {error_msg}",
            "model_name": model_name,
            "error": error_msg,
            "progress_key": progress_key
        }

@router.get("/spacy/models/download/progress/{progress_key}")
def get_spacy_download_progress(progress_key: str):
    """spaCy 모델 다운로드 진행률을 스트리밍합니다."""
    
    def generate_progress() -> Iterator[str]:
        max_wait_time = 300  # 5분 최대 대기
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            if progress_key in download_progress:
                progress_data = download_progress[progress_key]
                
                # 서버 로그에 진행률 기록
                if progress_data["progress"] % 20 == 0 or progress_data["status"] in ["completed", "error"]:
                    logger.info(f"📊 spaCy 다운로드 진행률 - {progress_data['model_name']}: {progress_data['progress']}% ({progress_data['message']})")
                
                # SSE 형식으로 데이터 전송
                yield f"data: {json.dumps(progress_data)}\n\n"
                
                # 완료되거나 오류가 발생하면 종료
                if progress_data["status"] in ["completed", "error"]:
                    break
                    
            else:
                # 진행률 데이터가 없으면 종료
                yield f"data: {json.dumps({'status': 'not_found', 'message': '진행률 정보를 찾을 수 없습니다'})}\n\n"
                break
            
            time.sleep(0.5)  # 0.5초마다 업데이트
        
        # 타임아웃 시
        if time.time() - start_time >= max_wait_time:
            yield f"data: {json.dumps({'status': 'timeout', 'message': '타임아웃이 발생했습니다'})}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@router.get("/spacy/models/{model_name}/status")
def get_spacy_model_status(model_name: str) -> Dict[str, Any]:
    """spaCy 모델의 설치 상태를 확인합니다."""
    try:
        import spacy
        
        # 모델 로드 시도
        try:
            nlp = spacy.load(model_name)
            
            # 모델 정보 수집
            model_info = {
                "lang": nlp.lang,
                "pipeline": nlp.pipe_names,
                "version": getattr(nlp.meta, 'version', 'unknown'),
                "size": len(nlp.vocab)  # 어휘 크기
            }
            
            return {
                "status": "success",
                "model_name": model_name,
                "is_installed": True,
                "model_info": model_info
            }
            
        except OSError:
            return {
                "status": "success",
                "model_name": model_name,
                "is_installed": False,
                "message": f"모델 '{model_name}'이 설치되지 않았습니다"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"모델 상태 확인 실패: {str(e)}",
            "model_name": model_name,
            "error": str(e)
        }