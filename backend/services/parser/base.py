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
    dcterms_available: Optional[str] = None  # 공개일
    dcterms_accessrights: Optional[str] = None  # 접근 권한
    
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
    
    def to_schema_compliant_dict(self, file_id: int, project_id: Optional[int] = None) -> Dict[str, Any]:
        """메타데이터 스키마 규격에 맞는 딕셔너리로 변환"""
        from datetime import datetime
        import uuid
        
        # 기본 메타데이터 구성
        metadata = {
            "@context": "http://purl.org/dc/terms/",
        }
        
        # 필수 필드들 (스키마 요구사항)
        metadata.update({
            "dc:title": self.dc_title or self.title or self.file_name or "Untitled Document",
            "dc:identifier": self.dc_identifier or f"file-{file_id}-{uuid.uuid4().hex[:8]}",
            "dc:creator": self.dc_creator or self.author or "Unknown",
            "dc:type": self._map_document_type(self.dc_type or self.doc_type_code),
            "dc:format": self.dc_format or self.mime_type or self._guess_mime_type(),
            "dc:language": self.dc_language or self._detect_language(),
            "dcterms:created": self._format_datetime(self.dcterms_created or self.created_date),
        })
        
        # 선택 필드들 (null이 아닌 것만)
        optional_fields = {
            # 설명 정보
            "dc:description": self.dc_description,
            "dc:subject": self._format_subject_array(self.dc_subject),
            "dc:publisher": self.dc_publisher,
            "dc:contributor": self._format_contributor_array(self.dc_contributor),
            
            # 권한 정보
            "dc:rights": self.dc_rights,
            "dcterms:accessRights": self.dcterms_accessrights or "public",
            
            # 시간 정보
            "dcterms:modified": self._format_datetime(self.dcterms_modified or self.modified_date),
            "dcterms:available": self._format_date(self.dcterms_available),
            
            # 관계 정보
            "dc:source": self._format_source_array(self.dc_source),
            "dc:relation": self._format_relation_array(self.dc_relation),
            
            # 파일 정보
            "file:name": self.file_name,
            "file:size": self.file_size,
            "doc:pageCount": self.doc_page_count or self.page_count,
            
            # 확장 정보
            "dcterms:extent": self._format_extent(),
            "dcterms:medium": self.dcterms_medium or "digital",
            "dcterms:alternative": self.file_name,
            "dcterms:isPartOf": f"project_{project_id}" if project_id else None,
            "dcterms:hasFormat": self.file_extension,
            
            # 문서 특정 정보
            "doc:wordCount": self.doc_word_count or self.word_count,
            "doc:characterCount": self.doc_character_count,
            "doc:typeCode": self.doc_type_code,
            "doc:supported": self.doc_supported or "yes",
            
            # 처리 정보
            "processing:parserName": self.parser_name,
            "processing:parserVersion": self.parser_version,
            "processing:extractionDate": datetime.now().isoformat(),
            "processing:appVersion": self.app_version or "1.0.0",
            "processing:parseStatus": "success",
        }
        
        # null이 아닌 값만 추가
        for key, value in optional_fields.items():
            if value is not None and value != "":
                metadata[key] = value
        
        return metadata
    
    def _map_document_type(self, doc_type: Optional[str]) -> str:
        """문서 타입을 Dublin Core 표준으로 매핑"""
        if not doc_type:
            return "Text"
        
        type_mapping = {
            "pdf": "Text",
            "docx": "Text", 
            "txt": "Text",
            "html": "Text",
            "md": "Text",
            "markdown": "Text",
            "image": "Image",
            "dataset": "Dataset",
            "software": "Software",
            "audio": "Sound",
            "video": "MovingImage",
        }
        
        return type_mapping.get(doc_type.lower(), "Text")
    
    def _guess_mime_type(self) -> str:
        """파일 확장자로 MIME 타입 추측"""
        if not self.file_extension:
            return "text/plain"
        
        mime_mapping = {
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".html": "text/html",
            ".htm": "text/html",
            ".md": "text/markdown",
            ".json": "application/json",
            ".xml": "application/xml",
        }
        
        return mime_mapping.get(self.file_extension.lower(), "text/plain")
    
    def _detect_language(self) -> str:
        """언어 감지 (기본값: 한국어)"""
        if self.dc_language:
            return self.dc_language
        
        # 한국어가 기본값이지만, 추후 실제 언어 감지 로직으로 교체 가능
        return "ko"
    
    def _format_datetime(self, dt_str: Optional[str]) -> Optional[str]:
        """DateTime을 ISO 8601 형식으로 포맷"""
        if not dt_str:
            return None
        
        try:
            # 이미 ISO 형식인지 확인
            if 'T' in dt_str and ('Z' in dt_str or '+' in dt_str[-6:]):
                return dt_str
            
            # 타임스탬프인 경우 변환
            if dt_str.replace('.', '').isdigit():
                from datetime import datetime
                dt = datetime.fromtimestamp(float(dt_str))
                return dt.isoformat() + "+09:00"
            
            # 기타 형식은 그대로 반환 (추후 파싱 로직 추가 가능)
            return dt_str
        except:
            return dt_str
    
    def _format_date(self, date_str: Optional[str]) -> Optional[str]:
        """Date를 YYYY-MM-DD 형식으로 포맷"""
        if not date_str:
            return None
        
        try:
            # 이미 YYYY-MM-DD 형식인지 확인
            if len(date_str) == 10 and date_str.count('-') == 2:
                return date_str
            
            # DateTime에서 Date 부분만 추출
            if 'T' in date_str:
                return date_str.split('T')[0]
            
            return date_str
        except:
            return date_str
    
    def _format_subject_array(self, subject: Optional[str]) -> Optional[list]:
        """주제를 배열 형식으로 변환"""
        if not subject:
            return None
        
        if isinstance(subject, list):
            return subject
        
        # 쉼표로 구분된 문자열을 배열로 변환
        return [s.strip() for s in subject.split(',') if s.strip()]
    
    def _format_contributor_array(self, contributor: Optional[str]) -> Optional[list]:
        """기여자를 배열 형식으로 변환"""
        return self._format_subject_array(contributor)
    
    def _format_source_array(self, source: Optional[str]) -> Optional[list]:
        """원본 소스를 배열 형식으로 변환"""
        if not source:
            return None
        
        if isinstance(source, list):
            return source
        
        return [source]
    
    def _format_relation_array(self, relation: Optional[str]) -> Optional[list]:
        """관련 자원을 배열 형식으로 변환"""
        return self._format_source_array(relation)
    
    def _format_extent(self) -> Optional[str]:
        """크기 정보를 문자열로 포맷"""
        if self.file_size:
            return f"{self.file_size} bytes"
        return None

@dataclass
class ParseResult:
    """파싱 결과"""
    text: str
    metadata: DocumentMetadata
    success: bool = True
    error_message: Optional[str] = None
    parser_name: str = ""
    md_file_path: Optional[str] = None  # 저장된 MD 파일 경로

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