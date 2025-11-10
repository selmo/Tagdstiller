"""
PDFDocling을 사용한 고급 PDF 파싱 모듈
테이블, 이미지, 구조를 보존하는 PDF 파서
"""

from pathlib import Path
from typing import Optional
import logging
from .base import DocumentParser, ParseResult, DocumentMetadata

logger = logging.getLogger(__name__)

class DoclingParser(DocumentParser):
    """
    PDFDocling을 사용한 PDF 파서
    - 테이블 구조 보존
    - 이미지 추출
    - 문서 레이아웃 보존
    - Markdown 변환 지원
    """
    
    def __init__(self):
        super().__init__("pdf_parser_docling")
        self.supported_extensions = ['.pdf']
        self.supported_mime_types = ['application/pdf']

    def _clean_markdown_for_llm(self, markdown_text: str) -> str:
        """LLM 처리를 위한 마크다운 정제

        - 특수 문자 이스케이프
        - 복잡한 테이블 단순화
        - HTML 주석 제거
        - 중복 공백 정리
        """
        import re

        # 1. HTML 주석 제거
        markdown_text = re.sub(r'<!--.*?-->', '', markdown_text, flags=re.DOTALL)

        # 2. 이미지 마커 제거
        markdown_text = re.sub(r'!\[.*?\]\(.*?\)', '[이미지]', markdown_text)

        # 3. 중괄호가 포함된 특수 패턴 정리 (LLM JSON 생성 시 혼란 방지)
        # 예: {변수명} → [변수명]
        markdown_text = re.sub(r'\{([^}]+)\}', r'[\1]', markdown_text)

        # 4. 연속된 공백을 하나로
        markdown_text = re.sub(r' +', ' ', markdown_text)

        # 5. 연속된 줄바꿈을 최대 2개로 제한
        markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)

        # 6. 테이블의 복잡한 정렬 마커 제거
        # |:---|:---:| → |---|---|
        markdown_text = re.sub(r'\|:?-+:?', '|---', markdown_text)

        # 7. 백슬래시 이스케이프 문제 방지
        # 단, 이미 이스케이프된 문자는 유지
        markdown_text = re.sub(r'\\(?![nrt"\\])', '', markdown_text)

        return markdown_text.strip()

    def parse(self, file_path: Path) -> ParseResult:
        """PDFDocling을 사용하여 PDF 파싱"""
        try:
            # Docling 라이브러리 동적 임포트
            try:
                from docling.document_converter import DocumentConverter
            except ImportError as e:
                logger.warning(f"PDFDocling이 설치되지 않았거나 임포트 오류: {e}")
                return self.fallback_parse(file_path)
            
            logger.info(f"📚 PDFDocling으로 파싱 시작: {file_path.name}")
            
            # 간단한 Docling 설정 (기본값 사용)
            # 문서 변환기 생성 (기본 설정 사용)
            converter = DocumentConverter()
            
            # PDF 파싱 (max_num_pages로 처리 제한)
            try:
                result = converter.convert(str(file_path), max_num_pages=50)
            except Exception as convert_error:
                logger.error(f"PDFDocling 파싱 오류: {convert_error}")
                # Docling은 필수이므로 오류가 발생해서는 안 됩니다
                raise Exception(f"Docling 파서 오류 - 모든 파서는 정상 작동해야 합니다: {convert_error}")
            
            # Markdown으로 변환
            try:
                markdown_text = result.document.export_to_markdown()
            except:
                # fallback to text export
                markdown_text = result.document.export_to_text()

            # LLM 처리를 위한 마크다운 정제
            markdown_text = self._clean_markdown_for_llm(markdown_text)
            logger.debug(f"🧹 마크다운 정제 완료")
            
            # 테이블 정보 추출
            tables = []
            try:
                for item in result.document.iterate_items():
                    if hasattr(item, 'label') and item.label == 'table':
                        tables.append({
                            'content': str(item.text) if hasattr(item, 'text') else '',
                            'page': item.prov[0].page if hasattr(item, 'prov') and item.prov else None
                        })
            except Exception as e:
                logger.warning(f"테이블 추출 실패: {e}")
            
            # 이미지 정보 추출
            images = []
            try:
                for item in result.document.iterate_items():
                    if hasattr(item, 'label') and item.label == 'figure':
                        images.append({
                            'caption': item.text if hasattr(item, 'text') else None,
                            'page': item.prov[0].page if hasattr(item, 'prov') and item.prov else None
                        })
            except Exception as e:
                logger.warning(f"이미지 정보 추출 실패: {e}")
            
            # 메타데이터 생성
            doc_metadata = {}
            if hasattr(result.document, 'metadata'):
                doc_metadata = result.document.metadata if isinstance(result.document.metadata, dict) else {}
            
            # DocumentMetadata에 전달할 기본 필드만 사용
            metadata = DocumentMetadata(
                title=doc_metadata.get('title', file_path.stem),
                page_count=doc_metadata.get('page_count', 1),
                word_count=len(markdown_text.split()),
                file_size=file_path.stat().st_size,
                mime_type='application/pdf',
                parser_name=self.parser_name,
                parser_version="1.0"
            )
            
            # 추가 메타데이터를 별도 속성으로 설정
            if doc_metadata.get('author'):
                metadata.dc_creator = doc_metadata.get('author')
            if doc_metadata.get('subject'):
                metadata.dc_subject = doc_metadata.get('subject')
            if doc_metadata.get('keywords'):
                metadata.dc_keywords = doc_metadata.get('keywords')
            if doc_metadata.get('created'):
                metadata.dc_date = doc_metadata.get('created')
                
            # Docling 특화 메타데이터
            metadata.tables_count = len(tables)
            metadata.images_count = len(images)
            metadata.has_ocr = False
            metadata.document_structure = {
                'tables': tables,
                'images': images,
                'sections': self.extract_sections_from_markdown(markdown_text)
            }
            
            logger.info(f"✅ PDFDocling 파싱 성공: {len(markdown_text)} 문자, {len(tables)} 테이블, {len(images)} 이미지")
            
            # Docling 결과를 MD 파일로 저장
            md_file_path = self._save_as_markdown(file_path, markdown_text)
            
            return ParseResult(
                text=markdown_text,
                metadata=metadata,
                success=True,
                parser_name=self.parser_name,
                md_file_path=md_file_path
            )
            
        except Exception as e:
            logger.error(f"PDFDocling 파싱 실패: {e}")
            return self.fallback_parse(file_path)
    
    def fallback_parse(self, file_path: Path) -> ParseResult:
        """Docling이 실패할 경우 기본 pypdf 사용"""
        try:
            import pypdf
            
            logger.info("📄 Fallback: pypdf로 파싱 시도")
            
            reader = pypdf.PdfReader(str(file_path))
            text_parts = []
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")
            
            text = '\n\n'.join(text_parts)
            
            # 기본 메타데이터
            metadata = DocumentMetadata(
                title=file_path.stem,
                page_count=len(reader.pages),
                word_count=len(text.split()),
                file_size=file_path.stat().st_size,
                mime_type='application/pdf',
                parser_name="pypdf_fallback",
                parser_version="1.0"
            )
            
            return ParseResult(
                text=text,
                metadata=metadata,
                success=True,
                parser_name="pypdf_fallback"
            )
            
        except Exception as e:
            logger.error(f"Fallback 파싱도 실패: {e}")
            return ParseResult(
                text="",
                metadata=None,
                success=False,
                error_message=str(e),
                parser_name=self.parser_name
            )
    
    def extract_sections_from_markdown(self, markdown_text: str) -> list:
        """Markdown 텍스트에서 섹션 구조 추출"""
        import re
        
        sections = []
        lines = markdown_text.split('\n')
        
        for i, line in enumerate(lines):
            # Markdown 헤더 감지
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                if title:
                    sections.append({
                        'level': level,
                        'title': title,
                        'line': i + 1
                    })
        
        return sections
    
    def _save_as_markdown(self, original_file_path: Path, markdown_content: str) -> str:
        """Docling 파싱 결과를 MD 파일로 저장"""
        try:
            # 파일별 전용 디렉토리 생성 (filename_without_extension/)
            output_dir = original_file_path.parent / original_file_path.stem
            output_dir.mkdir(exist_ok=True)
            
            # MD 파일 경로 생성 (filename_without_extension/docling.md)
            md_file_path = output_dir / "docling.md"
            
            # MD 파일로 저장
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {original_file_path.stem}\n\n")
                f.write(f"**파서:** Docling\n")
                f.write(f"**생성일시:** {self._get_current_time()}\n")
                f.write(f"**원본파일:** {original_file_path.name}\n\n")
                f.write("---\n\n")
                f.write(markdown_content)
            
            logger.info(f"📝 Docling MD 파일 저장 완료: {md_file_path}")
            return str(md_file_path)
            
        except Exception as e:
            logger.warning(f"⚠️ MD 파일 저장 실패: {e}")
            return None
    
    def _get_current_time(self) -> str:
        """현재 시간을 문자열로 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")