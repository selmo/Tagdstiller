from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DocumentMetadata:
    """문서 메타데이터"""
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    encoding: Optional[str] = None

@dataclass
class ParseResult:
    """파싱 결과"""
    text: str
    metadata: DocumentMetadata
    success: bool = True
    error_message: Optional[str] = None
    parser_name: str = ""

class DocumentParser(ABC):
    """
    문서 파서 인터페이스
    모든 문서 파서는 이 클래스를 상속받아 구현해야 합니다.
    """
    
    def __init__(self, parser_name: str):
        self.parser_name = parser_name
        self.supported_extensions = []
        self.supported_mime_types = []
    
    @abstractmethod
    def parse(self, file_path: Path) -> ParseResult:
        """
        파일을 파싱하여 텍스트를 추출합니다.
        
        Args:
            file_path: 파싱할 파일 경로
            
        Returns:
            ParseResult: 파싱 결과 (텍스트, 메타데이터, 성공 여부)
        """
        pass
    
    def can_parse(self, file_path: Path, mime_type: Optional[str] = None) -> bool:
        """
        이 파서가 해당 파일을 파싱할 수 있는지 확인합니다.
        
        Args:
            file_path: 파일 경로
            mime_type: MIME 타입 (선택사항)
            
        Returns:
            bool: 파싱 가능 여부
        """
        # 확장자 확인
        extension = file_path.suffix.lower()
        if extension in self.supported_extensions:
            return True
        
        # MIME 타입 확인
        if mime_type and mime_type in self.supported_mime_types:
            return True
        
        return False
    
    def get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """파일 기본 정보를 추출합니다."""
        try:
            stat = file_path.stat()
            return {
                "file_size": stat.st_size,
                "created_date": stat.st_ctime,
                "modified_date": stat.st_mtime,
                "extension": file_path.suffix.lower()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def create_error_result(self, error_message: str, file_path: Path) -> ParseResult:
        """에러 결과를 생성합니다."""
        file_info = self.get_file_info(file_path)
        metadata = DocumentMetadata(
            file_size=file_info.get("file_size"),
            created_date=str(file_info.get("created_date", "")),
            modified_date=str(file_info.get("modified_date", ""))
        )
        
        return ParseResult(
            text="",
            metadata=metadata,
            success=False,
            error_message=error_message,
            parser_name=self.parser_name
        )