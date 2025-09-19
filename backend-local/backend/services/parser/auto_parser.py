import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any, List
from .base import DocumentParser, ParseResult, DocumentMetadata
from .txt_parser import TxtParser
from .pdf_parser import PdfParser
from .docx_parser import DocxParser
from .html_parser import HtmlParser
from .md_parser import MarkdownParser
from .zip_parser import ZipParser

class AutoParser(DocumentParser):
    """자동 파일 형식 감지 파서"""
    
    def __init__(self):
        super().__init__("auto_parser")
        self.supported_extensions = []  # 모든 확장자 지원
        self.supported_mime_types = []  # 모든 MIME 타입 지원
        
        # 각 파서 인스턴스 생성
        self.parsers = {
            'txt': TxtParser(),
            'pdf': PdfParser(),
            'docx': DocxParser(),
            'html': HtmlParser(),
            'markdown': MarkdownParser(),
            'zip': ZipParser()
        }
        
        # 우선순위 매핑 (확장자 기반)
        self.extension_priority = {
            '.txt': ['txt'],
            '.text': ['txt'],
            '.log': ['txt'],
            '.csv': ['txt'],
            '.tsv': ['txt'],
            '.pdf': ['pdf'],
            '.docx': ['docx'],
            '.docm': ['docx'],
            '.html': ['html'],
            '.htm': ['html'],
            '.xhtml': ['html'],
            '.md': ['markdown'],
            '.markdown': ['markdown'],
            '.mdown': ['markdown'],
            '.mkd': ['markdown'],
            '.zip': ['zip']
        }
        
        # MIME 타입 매핑
        self.mime_type_mapping = {
            'text/plain': ['txt'],
            'text/csv': ['txt'],
            'application/pdf': ['pdf'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['docx'],
            'application/vnd.ms-word.document.macroEnabled.12': ['docx'],
            'text/html': ['html'],
            'application/xhtml+xml': ['html'],
            'text/markdown': ['markdown'],
            'text/x-markdown': ['markdown'],
            'application/zip': ['zip']
        }
    
    def parse(self, file_path: Path) -> ParseResult:
        """파일을 자동으로 감지하여 적절한 파서로 파싱합니다."""
        try:
            # 적절한 파서 찾기
            parser_names = self._detect_parser(file_path)
            
            if not parser_names:
                return self.create_error_result(
                    f"지원하지 않는 파일 형식입니다: {file_path.suffix}",
                    file_path
                )
            
            # 각 파서 시도 (우선순위 순)
            last_error = None
            for parser_name in parser_names:
                try:
                    parser = self.parsers[parser_name]
                    result = parser.parse(file_path)
                    
                    if result.success:
                        # 성공한 파서 정보 추가
                        result.parser_name = f"auto_parser -> {parser.parser_name}"
                        return result
                    else:
                        last_error = result.error_message
                        
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # 모든 파서가 실패한 경우
            return self.create_error_result(
                f"파일 파싱에 실패했습니다. 마지막 오류: {last_error}",
                file_path
            )
            
        except Exception as e:
            return self.create_error_result(f"자동 파싱 오류: {str(e)}", file_path)
    
    def _detect_parser(self, file_path: Path) -> List[str]:
        """파일에 적합한 파서들을 우선순위 순으로 반환합니다."""
        parser_candidates = []
        
        # 1. 확장자 기반 감지
        extension = file_path.suffix.lower()
        if extension in self.extension_priority:
            parser_candidates.extend(self.extension_priority[extension])
        
        # 2. MIME 타입 기반 감지
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type in self.mime_type_mapping:
            for parser_name in self.mime_type_mapping[mime_type]:
                if parser_name not in parser_candidates:
                    parser_candidates.append(parser_name)
        
        # 3. 파일 내용 기반 감지 (magic bytes)
        content_based = self._detect_by_content(file_path)
        for parser_name in content_based:
            if parser_name not in parser_candidates:
                parser_candidates.append(parser_name)
        
        # 4. 알려지지 않은 확장자의 경우 텍스트 파서를 마지막에 시도
        if not parser_candidates or extension not in self.extension_priority:
            if 'txt' not in parser_candidates:
                parser_candidates.append('txt')
        
        return parser_candidates
    
    def _detect_by_content(self, file_path: Path) -> List[str]:
        """파일 내용을 분석하여 파서를 감지합니다."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(1024)  # 첫 1KB 읽기
            
            parsers = []
            
            # PDF 매직 바이트
            if header.startswith(b'%PDF-'):
                parsers.append('pdf')
            
            # ZIP 기반 형식 (DOCX, ZIP)
            elif header.startswith(b'PK\x03\x04'):
                # DOCX는 ZIP 형식이므로 추가 확인 필요
                parsers.append('docx')
                parsers.append('zip')
            
            # HTML 감지
            elif b'<html' in header.lower() or b'<!doctype html' in header.lower():
                parsers.append('html')
            
            # Markdown 감지 (간단한 패턴)
            elif b'#' in header or b'```' in header or b'[' in header and b'](' in header:
                parsers.append('markdown')
            
            return parsers
            
        except Exception:
            return []
    
    def can_parse(self, file_path: Path, mime_type: Optional[str] = None) -> bool:
        """이 파서가 해당 파일을 파싱할 수 있는지 확인합니다."""
        # AutoParser는 모든 파일에 대해 시도할 수 있음
        return True
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """지원하는 파일 형식 정보를 반환합니다."""
        formats = {
            "extensions": [],
            "mime_types": [],
            "parsers": {}
        }
        
        for parser_name, parser in self.parsers.items():
            formats["parsers"][parser_name] = {
                "extensions": parser.supported_extensions,
                "mime_types": parser.supported_mime_types
            }
            
            formats["extensions"].extend(parser.supported_extensions)
            formats["mime_types"].extend(parser.supported_mime_types)
        
        # 중복 제거
        formats["extensions"] = list(set(formats["extensions"]))
        formats["mime_types"] = list(set(formats["mime_types"]))
        
        return formats
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """파일을 분석하여 상세 정보를 반환합니다."""
        try:
            analysis = {
                "file_path": str(file_path),
                "extension": file_path.suffix.lower(),
                "mime_type": mimetypes.guess_type(str(file_path))[0],
                "suggested_parsers": self._detect_parser(file_path),
                "file_info": self.get_file_info(file_path)
            }
            
            # 각 파서의 호환성 확인
            compatibility = {}
            for parser_name, parser in self.parsers.items():
                compatibility[parser_name] = parser.can_parse(file_path, analysis["mime_type"])
            
            analysis["parser_compatibility"] = compatibility
            
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def parse_with_specific_parser(self, file_path: Path, parser_name: str) -> ParseResult:
        """특정 파서를 사용하여 파싱합니다."""
        if parser_name not in self.parsers:
            return self.create_error_result(
                f"알 수 없는 파서: {parser_name}. 사용 가능한 파서: {list(self.parsers.keys())}",
                file_path
            )
        
        try:
            parser = self.parsers[parser_name]
            result = parser.parse(file_path)
            
            # 파서 이름 업데이트
            if result.success:
                result.parser_name = f"auto_parser -> {parser.parser_name}"
            
            return result
            
        except Exception as e:
            return self.create_error_result(
                f"특정 파서({parser_name}) 파싱 오류: {str(e)}",
                file_path
            )