from sqlalchemy.orm import Session
from db.models import Config
from typing import Dict, Any, Optional
import json
from .config_cache import config_cache

class ConfigService:
    """Service for managing application configuration."""
    
    # Default configuration values for keyword extraction and API settings
    DEFAULT_CONFIGS = {
        # Keyword extraction settings
        "extractor.default_method": {
            "value": "keybert",
            "description": "기본 추출 방법"
        },
        "extractor.keybert.enabled": {
            "value": "true",
            "description": "활성화"
        },
        "extractor.keybert.model": {
            "value": "all-MiniLM-L6-v2",
            "description": "모델"
        },
        "extractor.keybert.use_mmr": {
            "value": "true",
            "description": "MMR 사용"
        },
        "extractor.keybert.use_maxsum": {
            "value": "false",
            "description": "MaxSum 사용"
        },
        "extractor.keybert.diversity": {
            "value": "0.5",
            "description": "다양성 (0.0-1.0)"
        },
        "extractor.keybert.keyphrase_ngram_range": {
            "value": "[1, 2]",
            "description": "N-gram 범위"
        },
        "extractor.keybert.stop_words": {
            "value": "english",
            "description": "불용어 언어"
        },
        "extractor.keybert.max_keywords": {
            "value": "10",
            "description": "최대 키워드 수"
        },
        "extractor.ner.enabled": {
            "value": "true", 
            "description": "활성화"
        },
        "extractor.ner.model": {
            "value": "ko_core_news_sm",
            "description": "모델"
        },
        "extractor.ner.auto_download": {
            "value": "true",
            "description": "자동 다운로드"
        },
        "extractor.konlpy.enabled": {
            "value": "true",
            "description": "활성화"
        },
        "extractor.konlpy.tagger": {
            "value": "Okt",
            "description": "형태소 분석기"
        },
        "extractor.konlpy.min_length": {
            "value": "2",
            "description": "최소 글자 수"
        },
        "extractor.konlpy.min_frequency": {
            "value": "1",
            "description": "최소 빈도"
        },
        "extractor.konlpy.max_keywords": {
            "value": "15",
            "description": "최대 키워드 수"
        },
        
        # LLM 설정 (Ollama 통합)
        "OLLAMA_BASE_URL": {
            "value": "http://localhost:11434",
            "description": "서버 주소"
        },
        "OLLAMA_MODEL": {
            "value": "mistral",
            "description": "모델"
        },
        "OLLAMA_TIMEOUT": {
            "value": "30",
            "description": "타임아웃 (초)"
        },
        "OLLAMA_MAX_TOKENS": {
            "value": "1000",
            "description": "최대 토큰"
        },
        "OLLAMA_TEMPERATURE": {
            "value": "0.3",
            "description": "온도 (0.0-1.0)"
        },
        "ENABLE_LLM_EXTRACTION": {
            "value": "false",
            "description": "LLM 추출 활성화"
        },
        
        # OpenAI 설정
        "OPENAI_API_KEY": {
            "value": "",
            "description": "API 키"
        },
        "OPENAI_MODEL": {
            "value": "gpt-3.5-turbo",
            "description": "모델"
        },
        "OPENAI_MAX_TOKENS": {
            "value": "1000",
            "description": "최대 토큰"
        },
        
        # 파일 처리 설정
        "FILE_MAX_SIZE_MB": {
            "value": "50",
            "description": "최대 크기 (MB)"
        },
        "ALLOWED_EXTENSIONS": {
            "value": json.dumps([".txt", ".pdf", ".docx", ".html", ".md"]),
            "description": "허용 확장자"
        },
        
        # 기본 추출기 설정
        "DEFAULT_EXTRACTORS": {
            "value": json.dumps(["keybert", "ner", "konlpy"]),
            "description": "기본 추출기"
        },
        "MAX_KEYWORDS_PER_DOCUMENT": {
            "value": "20",
            "description": "문서당 최대 키워드"
        },
        
        # 일반 애플리케이션 설정
        "APP_DEBUG_MODE": {
            "value": "false",
            "description": "디버그 모드"
        }
    }
    
    @classmethod
    def initialize_default_configs(cls, db: Session) -> None:
        """Initialize default configuration values if they don't exist."""
        # 중복 설정 제거 및 마이그레이션
        deprecated_keys = [
            # 기존 ollama.* 설정들
            "ollama.base_url", "ollama.model", "ollama.timeout",
            # 중복 LLM 설정들
            "extractor.llm.enabled", "extractor.llm.provider", "extractor.llm.model", 
            "extractor.llm.max_tokens", "extractor.llm.temperature",
            "LLM_PROVIDER",  # ENABLE_LLM_EXTRACTION으로 통합
            # 중복 파일 설정들
            "file.allowed_extensions", "file.max_size_mb",
            # 중복 키워드 개수 설정들
            "app.max_keywords", "app.debug_mode",
            # 기존 OpenAI 설정들
            "openai.api_key", "openai.model", "openai.max_tokens",
            # 일관성 없는 KeyBERT 설정들
            "KeyBERT_ENABLED", "KeyBERT_MODEL", "KeyBERT_MMR"
        ]
        
        removed_count = 0
        for key in deprecated_keys:
            deprecated_config = db.query(Config).filter(Config.key == key).first()
            if deprecated_config:
                print(f"Removing deprecated config: {key}")
                db.delete(deprecated_config)
                removed_count += 1
        
        # 새 설정 추가
        added_count = 0
        for key, config_data in cls.DEFAULT_CONFIGS.items():
            existing_config = db.query(Config).filter(Config.key == key).first()
            if not existing_config:
                config = Config(
                    key=key,
                    value=config_data["value"],
                    description=config_data["description"]
                )
                db.add(config)
                added_count += 1
        
        db.commit()
        print(f"Configuration migration completed: removed {removed_count} deprecated configs, added {added_count} new configs")
    
    @classmethod
    def get_config_value(cls, db: Session, key: str, default: Any = None) -> Any:
        """Get a configuration value with optional default. Uses cache for performance."""
        return config_cache.get(key, default, db)
    
    @classmethod
    def get_bool_config(cls, db: Session, key: str, default: bool = False) -> bool:
        """Get a configuration value as boolean."""
        value = cls.get_config_value(db, key, default)
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)
    
    @classmethod
    def get_int_config(cls, db: Session, key: str, default: int = 0) -> int:
        """Get a configuration value as integer."""
        value = cls.get_config_value(db, key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @classmethod
    def get_float_config(cls, db: Session, key: str, default: float = 0.0) -> float:
        """Get a configuration value as float."""
        value = cls.get_config_value(db, key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @classmethod
    def get_json_config(cls, db: Session, key: str, default: Any = None) -> Any:
        """Get a configuration value as parsed JSON."""
        value = cls.get_config_value(db, key)
        if value is None:
            return default
        
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return default
    
    @classmethod
    def update_config(cls, db: Session, key: str, value: Any, description: Optional[str] = None) -> Config:
        """Update or create a configuration value. Updates cache automatically."""
        config = db.query(Config).filter(Config.key == key).first()
        
        # Convert value to string for storage
        str_value = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
        
        if config:
            config.value = str_value
            if description is not None:
                config.description = description
        else:
            config = Config(
                key=key,
                value=str_value,
                description=description
            )
            db.add(config)
        
        db.commit()
        db.refresh(config)
        
        # Update cache
        config_cache.set(key, value, db)
        
        return config
    
    @classmethod
    def _parse_config_value(cls, value: str) -> Any:
        """Parse a configuration value from string."""
        if not value:
            return value
        
        # Try to parse as JSON first (for lists, dicts, etc.)
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # Return as string if not valid JSON
            return value
    
    @classmethod
    def get_extractor_config(cls, db: Session) -> Dict[str, Any]:
        """Get all extractor-related configuration."""
        return {
            "default_method": cls.get_config_value(db, "extractor.default_method", "keybert"),
            "keybert_enabled": cls.get_bool_config(db, "extractor.keybert.enabled", True),
            "keybert_model": cls.get_config_value(db, "extractor.keybert.model", "all-MiniLM-L6-v2"),
            "keybert_use_mmr": cls.get_bool_config(db, "extractor.keybert.use_mmr", True),
            "keybert_use_maxsum": cls.get_bool_config(db, "extractor.keybert.use_maxsum", False),
            "keybert_diversity": cls.get_float_config(db, "extractor.keybert.diversity", 0.5),
            "keybert_keyphrase_ngram_range": cls.get_json_config(db, "extractor.keybert.keyphrase_ngram_range", [1, 2]),
            "keybert_stop_words": cls.get_config_value(db, "extractor.keybert.stop_words", "english"),
            "keybert_max_keywords": cls.get_int_config(db, "extractor.keybert.max_keywords", 10),
            "ner_enabled": cls.get_bool_config(db, "extractor.ner.enabled", True),
            "ner_model": cls.get_config_value(db, "extractor.ner.model", "ko_core_news_sm"),
            "ner_auto_download": cls.get_bool_config(db, "extractor.ner.auto_download", True),
            "llm_enabled": cls.get_bool_config(db, "ENABLE_LLM_EXTRACTION", False),
            "llm_provider": "ollama",
            "konlpy_enabled": cls.get_bool_config(db, "extractor.konlpy.enabled", False),
            "max_keywords": cls.get_int_config(db, "app.max_keywords", 20)
        }
    
    @classmethod
    def get_ollama_config(cls, db: Session) -> Dict[str, Any]:
        """Get Ollama-specific configuration."""
        return {
            "base_url": cls.get_config_value(db, "OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": cls.get_config_value(db, "OLLAMA_MODEL", "mistral"),
            "timeout": cls.get_int_config(db, "OLLAMA_TIMEOUT", 30)
        }