from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

@dataclass
class DocumentMetadata:
    """문서 메타데이터 (Dublin Core 기반)"""
    # 기존 필드 (호환성 유지)
    title: Optional[str] = None
    author: Optional[str] = None
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    encoding: Optional[str] = None
    
    # Dublin Core 메타데이터
    dc_title: Optional[str] = None  # 문서 제목
    dc_creator: Optional[str] = None  # 주 저작자/작성자
    dc_subject: Optional[str] = None  # 주제/키워드
    dc_description: Optional[str] = None  # 문서 설명
    dc_publisher: Optional[str] = None  # 발행자
    dc_contributor: Optional[str] = None  # 기여자
    dc_date: Optional[str] = None  # 생성/발행 날짜
    dc_type: Optional[str] = None  # 문서 타입
    dc_format: Optional[str] = None  # 파일 형식/MIME 타입
    dc_identifier: Optional[str] = None  # 고유 식별자
    dc_source: Optional[str] = None  # 원본 소스
    dc_language: Optional[str] = None  # 언어
    dc_relation: Optional[str] = None  # 관련 자료
    dc_coverage: Optional[str] = None  # 적용 범위
    dc_rights: Optional[str] = None  # 권리/라이선스
    
    # Dublin Core Terms 확장
    dcterms_created: Optional[str] = None  # 생성 날짜
    dcterms_modified: Optional[str] = None  # 수정 날짜
    dcterms_extent: Optional[str] = None  # 크기/범위
    dcterms_medium: Optional[str] = None  # 매체
    dcterms_audience: Optional[str] = None  # 대상 독자
    
    # 파일 관련 메타데이터
    file_name: Optional[str] = None  # 파일명
    file_path: Optional[str] = None  # 파일 경로
    file_extension: Optional[str] = None  # 파일 확장자
    
    # 문서 관련 메타데이터
    doc_page_count: Optional[int] = None  # 페이지 수
    doc_word_count: Optional[int] = None  # 단어 수
    doc_character_count: Optional[int] = None  # 문자 수
    doc_type_code: Optional[str] = None  # 문서 타입 코드
    doc_supported: Optional[str] = None  # 지원 여부
    
    # 애플리케이션 메타데이터
    app_version: Optional[str] = None  # 애플리케이션 버전
    
    # 파서 관련 정보
    parser_name: Optional[str] = None  # 사용된 파서명
    parser_version: Optional[str] = None  # 파서 버전

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