from pathlib import Path
from typing import Optional, List, Tuple
import logging
from .base import DocumentParser, ParseResult, DocumentMetadata
from utils.text_cleaner import TextCleaner

class PdfParser(DocumentParser):
    """PDF 파일 파서 (다중 엔진 지원)"""
    
    def __init__(self):
        super().__init__("pdf_parser")
        self.supported_extensions = ['.pdf']
        self.supported_mime_types = ['application/pdf']
        self.logger = logging.getLogger(__name__)
    
    def parse(self, file_path: Path) -> ParseResult:
        """PDF 파일을 다중 엔진으로 파싱합니다."""
        try:
            self.logger.info(f"📖 PDF 파싱 시작: {file_path.name}")
            
            # 파일 기본 정보
            file_info = self.get_file_info(file_path)
            
            # 여러 PDF 파싱 엔진을 순서대로 시도
            parsing_engines = [
                ("docling", self._parse_with_docling),  # Docling 최우선 (테이블/이미지 보존)
                ("pymupdf4llm", self._parse_with_pymupdf4llm),
                ("pdfplumber", self._parse_with_pdfplumber),
                ("pymupdf_advanced", self._parse_with_pymupdf_advanced),
                ("pymupdf_basic", self._parse_with_pymupdf_basic),
                ("pypdf2", self._parse_with_pypdf2)
            ]
            
            best_result = None
            best_score = 0
            
            for engine_name, parse_func in parsing_engines:
                try:
                    self.logger.info(f"🔄 {engine_name} 엔진으로 시도 중...")
                    text, metadata_dict = parse_func(file_path)
                    
                    if text and text.strip():
                        # 텍스트 품질 평가
                        quality_score = self._evaluate_text_quality(text)
                        self.logger.info(f"📊 {engine_name} 품질 점수: {quality_score:.2f} (길이: {len(text)})")
                        
                        if quality_score > best_score:
                            best_score = quality_score
                            best_result = (text, metadata_dict, engine_name)
                            
                            # 품질이 충분히 좋으면 더 이상 시도하지 않음
                            if quality_score > 0.8:
                                self.logger.info(f"✅ {engine_name} 엔진으로 고품질 추출 성공")
                                break
                    else:
                        self.logger.warning(f"⚠️ {engine_name} 엔진에서 텍스트 추출 실패")
                        
                except Exception as e:
                    self.logger.warning(f"❌ {engine_name} 엔진 실패: {str(e)}")
                    continue
            
            if not best_result:
                return self.create_error_result("모든 PDF 파싱 엔진에서 텍스트 추출에 실패했습니다.", file_path)
            
            text, metadata_dict, used_engine = best_result
            self.logger.info(f"🎯 최종 선택: {used_engine} 엔진 (품질: {best_score:.2f})")
            
            # 텍스트 정제
            cleaned_text = TextCleaner.clean_text(text)
            word_count = len(cleaned_text.split()) if cleaned_text else 0
            
            # 확장된 메타데이터 생성
            from datetime import datetime
            import os
            
            # 앱 버전 가져오기 (환경변수 또는 기본값)
            app_version = os.getenv("APP_VERSION", "1.0.0")
            
            # 파일 날짜 변환
            file_stat = file_path.stat()
            created_timestamp = datetime.fromtimestamp(file_stat.st_ctime).isoformat()
            modified_timestamp = datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            
            # 텍스트 언어 감지 (간단한 휴리스틱)
            def detect_language(text_sample):
                if not text_sample:
                    return "unknown"
                # 한글 문자 비율 확인
                korean_chars = sum(1 for c in text_sample[:1000] if '\uAC00' <= c <= '\uD7A3')
                if korean_chars > len(text_sample[:1000]) * 0.1:
                    return "ko"
                # 영어 알파벳 비율 확인
                english_chars = sum(1 for c in text_sample[:1000] if c.isascii() and c.isalpha())
                if english_chars > len(text_sample[:1000]) * 0.5:
                    return "en"
                return "unknown"
                
            detected_language = detect_language(cleaned_text)
            
            # Dublin Core 메타데이터 매핑
            dc_title = metadata_dict.get('title') or file_path.stem
            dc_creator = metadata_dict.get('author')
            dc_date = metadata_dict.get('creationDate')
            
            metadata = DocumentMetadata(
                # 기존 필드 (호환성)
                title=dc_title,
                author=dc_creator,
                created_date=dc_date,
                modified_date=metadata_dict.get('modDate'),
                page_count=metadata_dict.get('page_count', 0),
                word_count=word_count,
                file_size=file_info.get("file_size"),
                mime_type="application/pdf",
                
                # Dublin Core 메타데이터
                dc_title=dc_title,
                dc_creator=dc_creator,
                dc_subject=metadata_dict.get('subject'),
                dc_description=metadata_dict.get('subject') or f"PDF 문서, {metadata_dict.get('page_count', 0)}페이지",
                dc_publisher=metadata_dict.get('producer'),
                dc_contributor=metadata_dict.get('author'),
                dc_date=dc_date,
                dc_type="document",
                dc_format="application/pdf",
                dc_identifier=file_path.name,
                dc_source=str(file_path),
                dc_language=detected_language,
                dc_rights=None,
                
                # Dublin Core Terms
                dcterms_created=dc_date,
                dcterms_modified=metadata_dict.get('modDate'),
                dcterms_extent=f"{file_info.get('file_size', 0)} bytes",
                dcterms_medium="digital",
                
                # 파일 메타데이터
                file_name=file_path.name,
                file_path=str(file_path),
                file_extension=file_path.suffix.lower(),
                
                # 문서 메타데이터
                doc_page_count=metadata_dict.get('page_count', 0),
                doc_word_count=word_count,
                doc_character_count=len(cleaned_text) if cleaned_text else 0,
                doc_type_code="pdf",
                doc_supported="yes",
                
                # 애플리케이션 메타데이터
                app_version=app_version,
                
                # 파서 정보
                parser_name=f"{self.parser_name}_{used_engine}",
                parser_version="1.0"
            )
            
            return ParseResult(
                text=cleaned_text,
                metadata=metadata,
                success=True,
                parser_name=f"{self.parser_name}_{used_engine}",
                md_file_path=best_result[1].get('md_file_path')
            )
            
        except Exception as e:
            self.logger.error(f"❌ PDF 파싱 중 치명적 오류 발생: {str(e)}")
            return self.create_error_result(f"PDF 파싱 오류: {str(e)}", file_path)
    
    def extract_page_text(self, file_path: Path, page_number: int) -> str:
        """특정 페이지의 텍스트만 추출합니다."""
        try:
            import fitz
            doc = fitz.open(str(file_path))
            
            if 0 <= page_number < doc.page_count:
                page = doc.load_page(page_number)
                text = page.get_text()
                doc.close()
                # 페이지별 텍스트도 정제
                return TextCleaner.clean_text(text)
            else:
                doc.close()
                return ""
                
        except Exception:
            return ""
    
    def get_pdf_info(self, file_path: Path) -> dict:
        """PDF 파일의 상세 정보를 반환합니다."""
        try:
            import fitz
            doc = fitz.open(str(file_path))
            
            info = {
                "page_count": doc.page_count,
                "metadata": doc.metadata,
                "is_encrypted": doc.needs_pass,
                "has_links": False,
                "has_images": False
            }
            
            # 첫 페이지에서 링크와 이미지 확인
            if doc.page_count > 0:
                first_page = doc.load_page(0)
                info["has_links"] = len(first_page.get_links()) > 0
                info["has_images"] = len(first_page.get_images()) > 0
            
            doc.close()
            return info
            
        except Exception as e:
            return {"error": str(e)}
    
    def _evaluate_text_quality(self, text: str) -> float:
        """텍스트 품질을 평가합니다 (0.0 ~ 1.0)"""
        if not text or not text.strip():
            return 0.0
        
        text = text.strip()
        total_chars = len(text)
        if total_chars == 0:
            return 0.0
        
        # 1. 정상 문자 비율 (한글, 영어, 숫자, 기본 구두점)
        normal_chars = 0
        for char in text:
            code_point = ord(char)
            if ((0x0020 <= code_point <= 0x007F) or    # 기본 라틴
                (0x00A0 <= code_point <= 0x00FF) or    # 라틴 확장
                (0xAC00 <= code_point <= 0xD7AF) or    # 한글 음절
                (0x4E00 <= code_point <= 0x9FFF) or    # CJK 한자
                (0x3000 <= code_point <= 0x303F)):     # CJK 구두점
                normal_chars += 1
        
        normal_ratio = normal_chars / total_chars
        
        # 2. 비정상 문자 비율 (깨진 문자들)
        suspicious_chars = 0
        for char in text:
            code_point = ord(char)
            if (0x0590 <= code_point <= 0x06FF or  # 셈족 문자
                0x0900 <= code_point <= 0x0DFF or  # 인도계 문자
                0xE000 <= code_point <= 0xF8FF or  # 사설 영역
                0xFFF0 <= code_point <= 0xFFFF):   # 특수 영역
                suspicious_chars += 1
        
        suspicious_ratio = suspicious_chars / total_chars
        
        # 3. 공백 비율 (너무 많으면 안 좋음)
        whitespace_chars = sum(1 for char in text if char.isspace())
        whitespace_ratio = whitespace_chars / total_chars
        
        # 4. 단어 비율 (의미있는 단어들)
        words = text.split()
        meaningful_words = sum(1 for word in words if len(word) >= 2 and any(c.isalnum() for c in word))
        word_ratio = meaningful_words / max(1, len(words))
        
        # 품질 점수 계산
        quality_score = (
            normal_ratio * 0.4 +                    # 정상 문자 비율 (40%)
            (1 - suspicious_ratio) * 0.3 +          # 비정상 문자 적을수록 좋음 (30%)
            min(0.3, 1 - whitespace_ratio) * 0.2 +  # 적당한 공백 비율 (20%)
            word_ratio * 0.1                        # 의미있는 단어 비율 (10%)
        )
        
        return max(0.0, min(1.0, quality_score))
    
    def _parse_with_docling(self, file_path: Path) -> Tuple[str, dict]:
        """PDFDocling으로 구조 보존 파싱 (테이블, 이미지 포함)"""
        try:
            from services.parser.docling_parser import DoclingParser
            
            docling_parser = DoclingParser()
            result = docling_parser.parse(file_path)
            
            if result.success:
                metadata = {}
                if result.metadata:
                    # 메타데이터를 딕셔너리로 변환
                    metadata = {
                        'title': result.metadata.title,
                        'author': result.metadata.author,
                        'page_count': result.metadata.page_count,
                        'tables_count': getattr(result.metadata, 'tables_count', 0),
                        'images_count': getattr(result.metadata, 'images_count', 0),
                        'document_structure': getattr(result.metadata, 'document_structure', {}),
                        'created': result.metadata.created_date,
                        'subject': getattr(result.metadata, 'dc_subject', None),
                        'keywords': getattr(result.metadata, 'keywords', None),
                        'md_file_path': result.md_file_path  # MD 파일 경로 포함
                    }
                
                # Markdown 형식 텍스트와 구조화된 메타데이터 반환
                return result.text, metadata
            else:
                raise Exception(f"Docling 파싱 실패: {result.error_message}")
                
        except Exception as e:
            # Docling 실패 시 다음 엔진으로 넘어감
            self.logger.debug(f"Docling 파싱 건너뜀: {e}")
            raise
    
    def _parse_with_pymupdf4llm(self, file_path: Path) -> Tuple[str, dict]:
        """PyMuPDF4LLM으로 고품질 텍스트 추출"""
        try:
            import pymupdf4llm
            markdown_text = pymupdf4llm.to_markdown(str(file_path))
            
            # pymupdf4llm 결과를 MD 파일로 저장
            md_file_path = self._save_pymupdf4llm_as_markdown(file_path, markdown_text)
            
            # 마크다운에서 일반 텍스트로 변환 (내부 처리용)
            import re
            # 마크다운 문법 제거
            plain_text = re.sub(r'#+\s*', '', markdown_text)  # 헤더
            plain_text = re.sub(r'\*\*(.*?)\*\*', r'\1', plain_text)  # 볼드
            plain_text = re.sub(r'\*(.*?)\*', r'\1', plain_text)  # 이탤릭
            plain_text = re.sub(r'`(.*?)`', r'\1', plain_text)  # 코드
            
            # 기본 메타데이터 (pymupdf4llm은 메타데이터 추출이 제한적)
            metadata = {
                'page_count': markdown_text.count('\n---\n') + 1 if '\n---\n' in markdown_text else 1,
                'md_file_path': md_file_path
            }
            
            return plain_text, metadata
            
        except ImportError:
            raise ImportError("pymupdf4llm이 설치되지 않았습니다")
        except Exception as e:
            raise Exception(f"PyMuPDF4LLM 파싱 실패: {str(e)}")
    
    def _parse_with_pdfplumber(self, file_path: Path) -> Tuple[str, dict]:
        """pdfplumber로 텍스트 추출"""
        try:
            import pdfplumber
            
            text_parts = []
            metadata = {}
            
            with pdfplumber.open(str(file_path)) as pdf:
                metadata['page_count'] = len(pdf.pages)
                
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            text = '\n\n'.join(text_parts)
            return text, metadata
            
        except ImportError:
            raise ImportError("pdfplumber가 설치되지 않았습니다")
        except Exception as e:
            raise Exception(f"pdfplumber 파싱 실패: {str(e)}")
    
    def _parse_with_pymupdf_advanced(self, file_path: Path) -> Tuple[str, dict]:
        """PyMuPDF로 고급 텍스트 추출 (레이아웃 고려)"""
        try:
            import fitz
            
            doc = fitz.open(str(file_path))
            text_parts = []
            metadata = doc.metadata.copy()
            metadata['page_count'] = doc.page_count
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                
                # 다양한 추출 방식 시도
                methods = [
                    lambda p: p.get_text("text"),      # 기본 텍스트
                    lambda p: p.get_text("dict"),      # 딕셔너리 형태
                    lambda p: p.get_text("blocks"),    # 블록 단위
                ]
                
                best_text = ""
                best_length = 0
                
                for method in methods:
                    try:
                        if method == methods[1]:  # dict 방식
                            result = method(page)
                            page_text = self._extract_text_from_dict(result)
                        elif method == methods[2]:  # blocks 방식
                            result = method(page)
                            page_text = self._extract_text_from_blocks(result)
                        else:  # 기본 텍스트
                            page_text = method(page)
                        
                        if page_text and len(page_text) > best_length:
                            best_text = page_text
                            best_length = len(page_text)
                            
                    except Exception:
                        continue
                
                if best_text.strip():
                    text_parts.append(best_text)
            
            doc.close()
            text = '\n\n'.join(text_parts)
            return text, metadata
            
        except ImportError:
            raise ImportError("PyMuPDF가 설치되지 않았습니다")
        except Exception as e:
            raise Exception(f"PyMuPDF 고급 파싱 실패: {str(e)}")
    
    def _parse_with_pymupdf_basic(self, file_path: Path) -> Tuple[str, dict]:
        """PyMuPDF로 기본 텍스트 추출"""
        try:
            import fitz
            
            doc = fitz.open(str(file_path))
            text_parts = []
            metadata = doc.metadata.copy()
            metadata['page_count'] = doc.page_count
            
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(page_text)
            
            doc.close()
            text = '\n\n'.join(text_parts)
            return text, metadata
            
        except ImportError:
            raise ImportError("PyMuPDF가 설치되지 않았습니다")
        except Exception as e:
            raise Exception(f"PyMuPDF 기본 파싱 실패: {str(e)}")
    
    def _parse_with_pypdf2(self, file_path: Path) -> Tuple[str, dict]:
        """PyPDF2로 텍스트 추출"""
        try:
            import PyPDF2
            
            text_parts = []
            metadata = {}
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                metadata['page_count'] = len(reader.pages)
                
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text)
            
            text = '\n\n'.join(text_parts)
            return text, metadata
            
        except ImportError:
            raise ImportError("PyPDF2가 설치되지 않았습니다")
        except Exception as e:
            raise Exception(f"PyPDF2 파싱 실패: {str(e)}")
    
    def _extract_text_from_dict(self, text_dict: dict) -> str:
        """PyMuPDF dict 결과에서 텍스트 추출"""
        text_parts = []
        
        if 'blocks' in text_dict:
            for block in text_dict['blocks']:
                if 'lines' in block:
                    for line in block['lines']:
                        if 'spans' in line:
                            line_text = ""
                            for span in line['spans']:
                                if 'text' in span:
                                    line_text += span['text']
                            if line_text.strip():
                                text_parts.append(line_text)
        
        return '\n'.join(text_parts)
    
    def _extract_text_from_blocks(self, blocks: list) -> str:
        """PyMuPDF blocks 결과에서 텍스트 추출"""
        text_parts = []
        
        for block in blocks:
            if len(block) > 4:  # 텍스트 블록인지 확인
                block_text = block[4]  # 텍스트는 5번째 요소
                if block_text.strip():
                    text_parts.append(block_text)
        
        return '\n'.join(text_parts)
    
    def _save_pymupdf4llm_as_markdown(self, original_file_path: Path, markdown_content: str) -> str:
        """PyMuPDF4LLM 파싱 결과를 MD 파일로 저장"""
        try:
            # 파일별 전용 디렉토리 생성 (filename_without_extension/)
            output_dir = original_file_path.parent / original_file_path.stem
            output_dir.mkdir(exist_ok=True)
            
            # MD 파일 경로 생성 (filename_without_extension/pymupdf4llm.md)
            md_file_path = output_dir / "pymupdf4llm.md"
            
            # MD 파일로 저장
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {original_file_path.stem}\n\n")
                f.write(f"**파서:** PyMuPDF4LLM\n")
                f.write(f"**생성일시:** {self._get_current_time()}\n")
                f.write(f"**원본파일:** {original_file_path.name}\n\n")
                f.write("---\n\n")
                f.write(markdown_content)
            
            self.logger.info(f"📝 PyMuPDF4LLM MD 파일 저장 완료: {md_file_path}")
            return str(md_file_path)
            
        except Exception as e:
            self.logger.warning(f"⚠️ PyMuPDF4LLM MD 파일 저장 실패: {e}")
            return None
    
    def _get_current_time(self) -> str:
        """현재 시간을 문자열로 반환"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")