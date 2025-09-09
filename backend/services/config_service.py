from sqlalchemy.orm import Session
from db.models import Config
from typing import Dict, Any, Optional
import json
import requests
import logging
from .config_cache import config_cache

class ConfigService:
    """Service for managing application configuration."""
    
    logger = logging.getLogger(__name__)
    
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
        
        # LLM 설정 (Provider + Ollama/OpenAI/Gemini)
        "LLM_PROVIDER": {
            "value": "ollama",
            "description": "LLM 제공자 (ollama|openai|gemini)"
        },
        # Ollama
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
        "OPENAI_BASE_URL": {
            "value": "https://api.openai.com/v1",
            "description": "API Base URL"
        },
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
        "OPENAI_TEMPERATURE": {
            "value": "0.2",
            "description": "온도 (0.0-1.0)"
        },

        # Gemini 설정
        "GEMINI_API_BASE": {
            "value": "https://generativelanguage.googleapis.com",
            "description": "API Base URL"
        },
        "GEMINI_API_KEY": {
            "value": "",
            "description": "API 키"
        },
        "GEMINI_MODEL": {
            "value": "models/gemini-1.5-pro",
            "description": "모델 이름 (v1beta)"
        },
        "GEMINI_MAX_TOKENS": {
            "value": "1000",
            "description": "최대 토큰"
        },
        "GEMINI_TEMPERATURE": {
            "value": "0.2",
            "description": "온도 (0.0-1.0)"
        },
        
        # 파일 처리 설정
        "FILE_MAX_SIZE_MB": {
            "value": "50",
            "description": "최대 크기 (MB)"
        },
        "ALLOWED_EXTENSIONS": {
            "value": json.dumps([".txt", ".pdf", ".docx", ".html", ".md", ".hwp"]),
            "description": "허용 확장자"
        },
        
        # LangExtract 설정 (API 호환성 문제로 비활성화)
        "extractor.langextract.enabled": {
            "value": "false",
            "description": "활성화"
        },
        "extractor.langextract.max_keywords": {
            "value": "15",
            "description": "최대 키워드 수"
        },
        "extractor.langextract.chunk_size": {
            "value": "2000",
            "description": "청크 크기"
        },
        "extractor.langextract.overlap": {
            "value": "200",
            "description": "청크 오버랩"
        },
        "extractor.langextract.confidence_threshold": {
            "value": "0.6",
            "description": "신뢰도 임계값 (0.0-1.0)"
        },
        
        # Metadata 추출기 설정
        "extractor.metadata.enabled": {
            "value": "true",
            "description": "활성화"
        },
        "extractor.metadata.extract_structure": {
            "value": "true",
            "description": "구조 메타데이터 추출"
        },
        "extractor.metadata.extract_statistics": {
            "value": "true", 
            "description": "통계 메타데이터 추출"
        },
        "extractor.metadata.extract_content": {
            "value": "true",
            "description": "콘텐츠 메타데이터 추출"
        },
        "extractor.metadata.extract_file_info": {
            "value": "true",
            "description": "파일 메타데이터 추출"
        },
        "extractor.metadata.extract_summary": {
            "value": "true",
            "description": "문서 요약 메타데이터 추출"
        },
        "extractor.metadata.llm_summary": {
            "value": "true",
            "description": "LLM 기반 요약 사용 (비활성화 시 규칙 기반 요약)"
        },
        "extractor.metadata.include_filename": {
            "value": "true",
            "description": "파일명 키워드 포함"
        },
        "extractor.metadata.min_heading_length": {
            "value": "2",
            "description": "최소 제목 길이"
        },
        "extractor.metadata.max_metadata_keywords": {
            "value": "20",
            "description": "최대 메타데이터 키워드 수"
        },
        
        # 프롬프트 템플릿 설정
        "prompt.keyword_extraction.language": {
            "value": "auto",
            "description": "키워드 추출 프롬프트 언어 (auto, ko, en)"
        },
        "prompt.keyword_extraction.domain": {
            "value": "general",
            "description": "키워드 추출 도메인 (general, academic, technical)"
        },
        "prompt.keyword_extraction.max_keywords": {
            "value": "20",
            "description": "키워드 추출 최대 개수"
        },
        "prompt.keyword_extraction.temperature": {
            "value": "0.1",
            "description": "키워드 추출 LLM 온도"
        },
        "prompt.keyword_extraction.max_tokens": {
            "value": "500",
            "description": "키워드 추출 최대 토큰 수"
        },
        "prompt.document_summary.language": {
            "value": "auto",
            "description": "문서 요약 프롬프트 언어 (auto, ko, en)"
        },
        "prompt.document_summary.domain": {
            "value": "general",
            "description": "문서 요약 도메인 (general, academic, technical)"
        },
        "prompt.document_summary.temperature": {
            "value": "0.3",
            "description": "문서 요약 LLM 온도"
        },
        "prompt.document_summary.max_tokens": {
            "value": "1000",
            "description": "문서 요약 최대 토큰 수"
        },
        "prompt.document_summary.chunk_size": {
            "value": "4000",
            "description": "문서 청킹 크기"
        },
        "prompt.metadata_extraction.language": {
            "value": "ko",
            "description": "메타데이터 추출 프롬프트 언어"
        },
        "prompt.metadata_extraction.temperature": {
            "value": "0.2",
            "description": "메타데이터 추출 LLM 온도"
        },
        "prompt.metadata_extraction.max_tokens": {
            "value": "800",
            "description": "메타데이터 추출 최대 토큰 수"
        },
        
        # 커스텀 프롬프트 저장 공간
        "custom_prompts": {
            "value": "{}",
            "description": "사용자 정의 프롬프트 템플릿"
        },
        
        # 기본 추출기 설정 (LLM만 사용)
        "DEFAULT_EXTRACTORS": {
            "value": json.dumps(["llm"]),
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
        },
        
        # 로컬 파일 분석 설정
        "LOCAL_FILE_ROOT": {
            "value": "./data/uploads",
            "description": "로컬 파일 분석 루트 디렉토리"
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
            # 사용: LLM_PROVIDER (삭제하지 않음)
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
        
        # Ollama 서버 연결 테스트 (일시 비활성화 - startup 속도 개선)
        # cls._test_ollama_connection(db)
        print("ℹ️ Ollama 연결 테스트 건너뜀 - /llm/test_connection API로 수동 테스트 가능")
    
    @classmethod
    def _check_and_configure_ollama(cls, db: Session) -> None:
        """Check Ollama server connection and configure default model."""
        cls.logger.info("🔍 Ollama 서버 연결 테스트 시작...")
        print("🔍 Ollama 서버 연결 테스트 시작...")
        try:
            ollama_url = cls.get_config_value(db, "OLLAMA_BASE_URL", "http://localhost:11434")
            current_model = cls.get_config_value(db, "OLLAMA_MODEL", "mistral")
            cls.logger.info(f"📍 Ollama URL: {ollama_url}, 현재 모델: {current_model}")
            print(f"📍 Ollama URL: {ollama_url}, 현재 모델: {current_model}")
            
            # Ollama 서버 연결 테스트 (더 짧은 타임아웃으로 빠른 실패)
            response = requests.get(f"{ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                available_models = [model['name'] for model in response.json().get('models', [])]
                
                if available_models:
                    cls.logger.info(f"Ollama 서버 연결 성공. 사용 가능한 모델: {len(available_models)}개")
                    
                    # 현재 설정된 모델이 사용 가능한지 확인
                    if current_model not in available_models:
                        # 우선순위에 따라 자동 선택
                        preferred_models = [
                            "phi3.5:latest", "phi3:latest", "mistral:latest", "llama3.2:latest",
                            "qwen2.5:latest", "gemma2:latest", "deepseek-r1:latest"
                        ]
                        
                        selected_model = None
                        for preferred in preferred_models:
                            if preferred in available_models:
                                selected_model = preferred
                                break
                        
                        # 우선순위 모델이 없으면 첫 번째 모델 선택
                        if not selected_model:
                            selected_model = available_models[0]
                        
                        # 모델 업데이트
                        config = db.query(Config).filter(Config.key == "OLLAMA_MODEL").first()
                        if config:
                            old_model = config.value
                            config.value = selected_model
                            db.commit()
                            config_cache.invalidate("OLLAMA_MODEL")
                            cls.logger.info(f"🔄 Ollama 모델 자동 변경: {old_model} → {selected_model}")
                            print(f"🔄 Ollama 모델 자동 변경: {old_model} → {selected_model}")
                    else:
                        cls.logger.info(f"✅ Ollama 모델 '{current_model}' 사용 가능")
                        print(f"✅ Ollama 모델 '{current_model}' 사용 가능")
                else:
                    cls.logger.warning("⚠️ Ollama에 설치된 모델이 없습니다")
                    print("⚠️ Ollama에 설치된 모델이 없습니다")
            else:
                cls.logger.warning(f"⚠️ Ollama 서버 응답 오류: HTTP {response.status_code}")
                print(f"⚠️ Ollama 서버 응답 오류: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            cls.logger.warning("⚠️ Ollama 서버에 연결할 수 없습니다. LLM 기능을 사용하려면 Ollama를 시작하세요.")
            print("⚠️ Ollama 서버에 연결할 수 없습니다. LLM 기능을 사용하려면 Ollama를 시작하세요.")
        except requests.exceptions.Timeout:
            cls.logger.warning("⚠️ Ollama 서버 연결 타임아웃")
            print("⚠️ Ollama 서버 연결 타임아웃")
        except Exception as e:
            cls.logger.error(f"❌ Ollama 설정 확인 중 오류: {e}")
            print(f"❌ Ollama 설정 확인 중 오류: {e}")
    
    @classmethod
    def _test_ollama_connection(cls, db: Session) -> None:
        """Test Ollama server connection using /api/tags endpoint."""
        try:
            ollama_url = cls.get_config_value(db, "OLLAMA_BASE_URL", "http://localhost:11434")
            
            # 짧은 타임아웃으로 빠른 연결 테스트
            response = requests.get(f"{ollama_url}/api/tags", timeout=1)
            if response.status_code == 200:
                model_count = len(response.json().get('models', []))
                cls.logger.info(f"✅ Ollama 서버 연결 성공 - {model_count}개 모델 사용 가능")
                print(f"✅ Ollama 서버 연결 성공 - {model_count}개 모델 사용 가능")
            else:
                cls.logger.warning(f"⚠️ Ollama 서버 응답 오류: HTTP {response.status_code}")
                print(f"⚠️ Ollama 서버 응답 오류: HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            cls.logger.info("ℹ️ Ollama 서버 미연결 (LLM 기능 비활성화)")
            print("ℹ️ Ollama 서버 미연결 (LLM 기능 비활성화)")
        except requests.exceptions.Timeout:
            cls.logger.warning("⚠️ Ollama 서버 연결 타임아웃")
            print("⚠️ Ollama 서버 연결 타임아웃")
        except Exception as e:
            cls.logger.warning(f"⚠️ Ollama 연결 테스트 오류: {e}")
            print(f"⚠️ Ollama 연결 테스트 오류: {e}")
    
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
            "llm_provider": cls.get_config_value(db, "LLM_PROVIDER", "ollama"),
            "konlpy_enabled": cls.get_bool_config(db, "extractor.konlpy.enabled", False),
            "konlpy_tagger": cls.get_config_value(db, "extractor.konlpy.tagger", "Okt"),
            "konlpy_min_length": cls.get_int_config(db, "extractor.konlpy.min_length", 2),
            "konlpy_min_frequency": cls.get_int_config(db, "extractor.konlpy.min_frequency", 1),
            "konlpy_max_keywords": cls.get_int_config(db, "extractor.konlpy.max_keywords", 15),
            
            # LangExtract 설정 (API 호환성 문제로 비활성화)
            "langextract_enabled": cls.get_bool_config(db, "extractor.langextract.enabled", False),
            "langextract_max_keywords": cls.get_int_config(db, "extractor.langextract.max_keywords", 15),
            "langextract_chunk_size": cls.get_int_config(db, "extractor.langextract.chunk_size", 2000),
            "langextract_overlap": cls.get_int_config(db, "extractor.langextract.overlap", 200),
            "langextract_confidence_threshold": cls.get_float_config(db, "extractor.langextract.confidence_threshold", 0.6),
            
            # Metadata 설정
            "metadata_enabled": cls.get_bool_config(db, "extractor.metadata.enabled", True),
            "metadata_extract_structure": cls.get_bool_config(db, "extractor.metadata.extract_structure", True),
            "metadata_extract_statistics": cls.get_bool_config(db, "extractor.metadata.extract_statistics", True),
            "metadata_extract_content": cls.get_bool_config(db, "extractor.metadata.extract_content", True),
            "metadata_extract_file_info": cls.get_bool_config(db, "extractor.metadata.extract_file_info", True),
            "metadata_extract_summary": cls.get_bool_config(db, "extractor.metadata.extract_summary", True),
            "metadata_llm_summary": cls.get_bool_config(db, "extractor.metadata.llm_summary", True),
            "metadata_include_filename": cls.get_bool_config(db, "extractor.metadata.include_filename", True),
            "metadata_min_heading_length": cls.get_int_config(db, "extractor.metadata.min_heading_length", 2),
            "metadata_max_metadata_keywords": cls.get_int_config(db, "extractor.metadata.max_metadata_keywords", 20),
            
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

    @classmethod
    def get_openai_config(cls, db: Session) -> Dict[str, Any]:
        return {
            "base_url": cls.get_config_value(db, "OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "api_key": cls.get_config_value(db, "OPENAI_API_KEY", ""),
            "model": cls.get_config_value(db, "OPENAI_MODEL", "gpt-3.5-turbo"),
            "max_tokens": cls.get_int_config(db, "OPENAI_MAX_TOKENS", 1000),
            "temperature": cls.get_float_config(db, "OPENAI_TEMPERATURE", 0.2),
        }

    @classmethod
    def get_gemini_config(cls, db: Session) -> Dict[str, Any]:
        return {
            "base_url": cls.get_config_value(db, "GEMINI_API_BASE", "https://generativelanguage.googleapis.com"),
            "api_key": cls.get_config_value(db, "GEMINI_API_KEY", ""),
            "model": cls.get_config_value(db, "GEMINI_MODEL", "models/gemini-1.5-pro"),
            "max_tokens": cls.get_int_config(db, "GEMINI_MAX_TOKENS", 1000),
            "temperature": cls.get_float_config(db, "GEMINI_TEMPERATURE", 0.2),
        }
