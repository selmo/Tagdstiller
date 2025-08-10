import chardet
from pathlib import Path
from typing import Optional
from .base import DocumentParser, ParseResult, DocumentMetadata
from utils.text_cleaner import TextCleaner

class TxtParser(DocumentParser):
    """일반 텍스트 파일 파서"""
    
    def __init__(self):
        super().__init__("txt_parser")
        self.supported_extensions = ['.txt', '.text', '.log', '.csv', '.tsv']
        self.supported_mime_types = [
            'text/plain',
            'text/csv',
            'text/tab-separated-values',
            'application/csv'
        ]
    
    def parse(self, file_path: Path) -> ParseResult:
        """텍스트 파일을 파싱합니다."""
        try:
            # 파일 기본 정보
            file_info = self.get_file_info(file_path)
            
            # 인코딩 감지
            encoding = self._detect_encoding(file_path)
            
            # 텍스트 읽기
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                raw_text = f.read()
            
            # 텍스트 정제 (비정상 문자 제거)
            text = TextCleaner.clean_text(raw_text)
            
            # 단어 수 계산
            word_count = len(text.split()) if text else 0
            
            # 메타데이터 생성
            metadata = DocumentMetadata(
                title=file_path.stem,
                word_count=word_count,
                file_size=file_info.get("file_size"),
                created_date=str(file_info.get("created_date", "")),
                modified_date=str(file_info.get("modified_date", "")),
                encoding=encoding,
                mime_type="text/plain"
            )
            
            return ParseResult(
                text=text,
                metadata=metadata,
                success=True,
                parser_name=self.parser_name
            )
            
        except Exception as e:
            return self.create_error_result(f"TXT 파싱 오류: {str(e)}", file_path)
    
    def _detect_encoding(self, file_path: Path) -> str:
        """파일의 인코딩을 감지합니다."""
        try:
            # 파일의 일부를 읽어서 인코딩 감지
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)  # 10KB 샘플
            
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            
            # 신뢰도가 낮거나 감지되지 않은 경우 기본값 사용
            if not encoding or result.get('confidence', 0) < 0.7:
                encoding = 'utf-8'
            
            return encoding
            
        except Exception:
            return 'utf-8'  # 기본값