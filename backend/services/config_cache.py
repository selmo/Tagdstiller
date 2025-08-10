from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from threading import Lock
from datetime import datetime, timedelta
import json
from db.models import Config

class ConfigCache:
    """
    설정 캐시 및 핫 리로드 관리 클래스
    
    앱 시작 시 설정을 로딩하고, 필요 시 핫 리로드를 지원합니다.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._last_updated: Dict[str, datetime] = {}
        self._lock = Lock()
        self._cache_ttl = timedelta(minutes=5)  # 5분 TTL
        self._is_initialized = False
    
    def initialize(self, db_session: Session) -> None:
        """캐시를 초기화합니다."""
        with self._lock:
            try:
                configs = db_session.query(Config).all()
                self._cache.clear()
                self._last_updated.clear()
                
                for config in configs:
                    parsed_value = self._parse_value(config.value, config.value_type)
                    self._cache[config.key] = parsed_value
                    self._last_updated[config.key] = config.updated_at
                
                self._is_initialized = True
                print(f"Config cache initialized with {len(self._cache)} settings")
                
            except Exception as e:
                print(f"Failed to initialize config cache: {e}")
                self._is_initialized = False
    
    def get(self, key: str, default: Any = None, db_session: Optional[Session] = None) -> Any:
        """
        설정 값을 가져옵니다.
        
        Args:
            key: 설정 키
            default: 기본값
            db_session: DB 세션 (핫 리로드용)
            
        Returns:
            설정 값 또는 기본값
        """
        with self._lock:
            # 캐시가 초기화되지 않은 경우
            if not self._is_initialized and db_session:
                self.initialize(db_session)
            
            # 캐시에서 값 조회
            if key in self._cache:
                # TTL 체크
                if self._should_refresh(key) and db_session:
                    self._refresh_key(key, db_session)
                
                return self._cache.get(key, default)
            
            # 캐시에 없는 경우 DB에서 직접 조회
            if db_session:
                return self._fetch_from_db(key, default, db_session)
            
            return default
    
    def set(self, key: str, value: Any, db_session: Session) -> None:
        """
        설정 값을 업데이트합니다.
        
        Args:
            key: 설정 키
            value: 설정 값
            db_session: DB 세션
        """
        with self._lock:
            try:
                # DB 업데이트
                config = db_session.query(Config).filter(Config.key == key).first()
                if config:
                    config.value = str(value)
                    config.updated_at = datetime.utcnow()
                else:
                    config = Config(
                        key=key,
                        value=str(value),
                        value_type=self._detect_value_type(value)
                    )
                    db_session.add(config)
                
                db_session.commit()
                
                # 캐시 업데이트
                self._cache[key] = value
                self._last_updated[key] = datetime.utcnow()
                
                print(f"Config updated: {key} = {value}")
                
            except Exception as e:
                db_session.rollback()
                print(f"Failed to update config {key}: {e}")
                raise
    
    def refresh_all(self, db_session: Session) -> None:
        """모든 설정을 새로고침합니다."""
        print("Refreshing all configs...")
        self.initialize(db_session)
    
    def refresh_key(self, key: str, db_session: Session) -> None:
        """특정 키의 설정을 새로고침합니다."""
        with self._lock:
            self._refresh_key(key, db_session)
    
    def get_all(self) -> Dict[str, Any]:
        """모든 캐시된 설정을 반환합니다."""
        with self._lock:
            return self._cache.copy()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """캐시 통계를 반환합니다."""
        with self._lock:
            return {
                "is_initialized": self._is_initialized,
                "total_keys": len(self._cache),
                "cache_keys": list(self._cache.keys()),
                "last_updated_count": len(self._last_updated),
                "ttl_minutes": self._cache_ttl.total_seconds() / 60
            }
    
    def _should_refresh(self, key: str) -> bool:
        """키가 새로고침이 필요한지 확인합니다."""
        if key not in self._last_updated:
            return True
        
        return datetime.utcnow() - self._last_updated[key] > self._cache_ttl
    
    def _refresh_key(self, key: str, db_session: Session) -> None:
        """키를 새로고침합니다."""
        try:
            config = db_session.query(Config).filter(Config.key == key).first()
            if config:
                parsed_value = self._parse_value(config.value, config.value_type)
                self._cache[key] = parsed_value
                self._last_updated[key] = config.updated_at
            else:
                # DB에서 삭제된 키는 캐시에서도 제거
                if key in self._cache:
                    del self._cache[key]
                if key in self._last_updated:
                    del self._last_updated[key]
                    
        except Exception as e:
            print(f"Failed to refresh key {key}: {e}")
    
    def _fetch_from_db(self, key: str, default: Any, db_session: Session) -> Any:
        """DB에서 직접 값을 가져옵니다."""
        try:
            config = db_session.query(Config).filter(Config.key == key).first()
            if config:
                parsed_value = self._parse_value(config.value, config.value_type)
                # 캐시에 저장
                self._cache[key] = parsed_value
                self._last_updated[key] = config.updated_at
                return parsed_value
            
            return default
            
        except Exception as e:
            print(f"Failed to fetch {key} from DB: {e}")
            return default
    
    def _parse_value(self, value: str, value_type: str) -> Any:
        """값 타입에 따라 파싱합니다."""
        if not value:
            return value
        
        try:
            if value_type == "int":
                return int(value)
            elif value_type == "float":
                return float(value)
            elif value_type == "bool":
                return value.lower() in ("true", "1", "yes", "on")
            elif value_type == "json":
                return json.loads(value)
            else:  # string
                return value
                
        except (ValueError, json.JSONDecodeError) as e:
            print(f"Failed to parse value '{value}' as {value_type}: {e}")
            return value
    
    def _detect_value_type(self, value: Any) -> str:
        """값의 타입을 감지합니다."""
        if isinstance(value, bool):
            return "bool"
        elif isinstance(value, int):
            return "int"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (dict, list)):
            return "json"
        else:
            return "string"

# 전역 설정 캐시 인스턴스
config_cache = ConfigCache()