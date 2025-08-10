from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel
from dataclasses import dataclass

@dataclass
class Keyword:
    """키워드 추출 결과"""
    text: str
    score: float
    extractor: str
    category: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    context_snippet: Optional[str] = None
    page_number: Optional[int] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None

class KeywordExtractor(ABC):
    """
    키워드 추출기 인터페이스
    모든 키워드 추출기는 이 클래스를 상속받아 구현해야 합니다.
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.is_loaded = False
    
    @abstractmethod
    def load_model(self) -> bool:
        """모델을 로드합니다."""
        pass
    
    @abstractmethod
    def extract(self, text: str, file_path: Optional[Path] = None) -> List[Keyword]:
        """
        텍스트에서 키워드를 추출합니다.
        
        Args:
            text: 분석할 텍스트
            file_path: 원본 파일 경로 (페이지/줄 번호 계산용, 선택사항)
            
        Returns:
            List[Keyword]: 추출된 키워드 목록
        """
        pass
    
    def is_available(self) -> bool:
        """추출기가 사용 가능한지 확인합니다."""
        return self.is_loaded
    
    def get_info(self) -> Dict[str, Any]:
        """추출기 정보를 반환합니다."""
        return {
            "name": self.name,
            "loaded": self.is_loaded,
            "config": self.config
        }