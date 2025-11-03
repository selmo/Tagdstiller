"""
Docling + 전체 페이지 OCR 통합 파서
- 스캔 문서 자동 감지
- 전체 페이지 OCR (한글 최적화)
- 적응형 이진화 및 고급 전처리
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging
import io

from .base import DocumentParser, ParseResult, DocumentMetadata

logger = logging.getLogger(__name__)

# OCR 관련 imports
try:
    import pytesseract
    import cv2
    import numpy as np
    from PIL import Image
    import fitz  # PyMuPDF
    OCR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"기본 OCR 라이브러리 임포트 실패: {e}")
    OCR_AVAILABLE = False

# EasyOCR 선택적 import
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    logger.info("✅ EasyOCR 사용 가능")
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.info("ℹ️ EasyOCR 미설치 (Tesseract 사용)")


class DoclingOCRParser(DocumentParser):
    """Docling + 전체 페이지 OCR 통합 파서"""

    def __init__(self, ocr_engine: str = "auto"):
        """
        Args:
            ocr_engine: OCR 엔진 선택
                - "auto": EasyOCR 우선, 실패 시 Tesseract 폴백 (기본값)
                - "easyocr": EasyOCR만 사용 (혼합 텍스트 최적)
                - "tesseract": Tesseract만 사용 (빠른 처리)
        """
        super().__init__("docling_ocr")
        self.supported_extensions = ['.pdf']
        self.supported_mime_types = ['application/pdf']
        self.ocr_engine = ocr_engine.lower()

        # EasyOCR reader 초기화 (한글+영문) - GPU/MPS 자동 감지
        self.easyocr_reader = None
        if EASYOCR_AVAILABLE and self.ocr_engine in ["auto", "easyocr"]:
            try:
                # GPU/MPS 사용 가능 여부 자동 감지
                import torch
                use_gpu = torch.cuda.is_available() or torch.backends.mps.is_available()
                device = 'cpu'

                if torch.cuda.is_available():
                    device = 'cuda'
                elif torch.backends.mps.is_available():
                    device = 'mps'

                self.easyocr_reader = easyocr.Reader(['ko', 'en'], gpu=use_gpu)
                logger.info(f"✅ EasyOCR Reader 초기화 완료 (한글+영문) - 디바이스: {device}, 모드: {self.ocr_engine}")
            except Exception as e:
                logger.warning(f"⚠️ EasyOCR Reader 초기화 실패: {e}")
                if self.ocr_engine == "easyocr":
                    logger.error("EasyOCR 전용 모드이나 초기화 실패, Tesseract로 폴백")

        if self.ocr_engine == "tesseract":
            logger.info("🔧 Tesseract 전용 모드로 실행")

    def parse(self, file_path: Path) -> ParseResult:
        """Docling + OCR 통합 파싱 (스캔 문서 자동 감지)"""
        try:
            if not OCR_AVAILABLE:
                logger.warning("OCR 라이브러리가 없어 기본 Docling 파서 사용")
                return self._docling_only_parse(file_path)

            logger.info(f"📚 Docling + OCR 통합 파싱 시작: {file_path.name}")

            # 1. Docling으로 문서 파싱
            docling_result = self._docling_parse(file_path)

            if not docling_result.success:
                logger.error("Docling 파싱 실패, 전체 페이지 OCR로 전환")
                return self._full_page_ocr_parse(file_path)

            # 2. 텍스트 품질 평가 (스캔 문서 감지)
            text_quality = self._evaluate_text_quality(docling_result.text)
            is_scanned = text_quality['is_scanned_document']

            logger.info(f"📊 텍스트 품질: 밀도={text_quality['text_density']:.3f}, "
                       f"이미지 태그={text_quality['image_tag_count']}개, "
                       f"스캔 문서={'예' if is_scanned else '아니오'}")

            if is_scanned:
                logger.info("📸 스캔 문서로 판단, 전체 페이지 OCR 모드로 전환")
                return self._full_page_ocr_parse(file_path)

            # 3. 일반 문서: Docling 결과 그대로 사용
            return docling_result

        except Exception as e:
            logger.error(f"Docling + OCR 파싱 실패: {e}", exc_info=True)
            return ParseResult(
                text="",
                metadata=None,
                success=False,
                error_message=str(e),
                parser_name=self.parser_name
            )

    def _docling_parse(self, file_path: Path) -> ParseResult:
        """Docling으로 기본 파싱"""
        try:
            from docling.document_converter import DocumentConverter

            converter = DocumentConverter()
            result = converter.convert(str(file_path), max_num_pages=100)
            markdown_text = result.document.export_to_markdown()

            doc_metadata = {}
            if hasattr(result.document, 'metadata'):
                doc_metadata = result.document.metadata if isinstance(result.document.metadata, dict) else {}

            metadata = DocumentMetadata(
                title=doc_metadata.get('title', file_path.stem),
                page_count=doc_metadata.get('page_count', 1),
                word_count=len(markdown_text.split()),
                file_size=file_path.stat().st_size,
                mime_type='application/pdf',
                parser_name=self.parser_name,
                parser_version="1.0+OCR"
            )

            return ParseResult(
                text=markdown_text,
                metadata=metadata,
                success=True,
                parser_name=self.parser_name
            )

        except Exception as e:
            logger.error(f"Docling 파싱 실패: {e}")
            return ParseResult(
                text="",
                metadata=None,
                success=False,
                error_message=str(e),
                parser_name=self.parser_name
            )

    def _evaluate_text_quality(self, text: str) -> Dict[str, Any]:
        """텍스트 품질 평가 및 스캔 문서 감지"""
        text_length = len(text.strip())
        image_tag_count = text.count('<!-- image -->')

        actual_text = text.replace('<!-- image -->', '').strip()
        actual_length = len(actual_text)

        text_density = actual_length / text_length if text_length > 0 else 0.0

        # 스캔 문서 판단: 텍스트 밀도 30% 미만 + 이미지 태그 10개 이상 + 실제 텍스트 500자 미만
        is_scanned = (text_density < 0.3 and image_tag_count >= 10 and actual_length < 500)

        return {
            'text_length': text_length,
            'actual_length': actual_length,
            'text_density': text_density,
            'image_tag_count': image_tag_count,
            'is_scanned_document': is_scanned
        }

    def _full_page_ocr_parse(self, file_path: Path) -> ParseResult:
        """전체 페이지 OCR 파싱 (한글 최적화)"""
        logger.info("📸 전체 페이지 OCR 모드 시작 (한글 최적화)")

        try:
            doc = fitz.open(str(file_path))
            total_pages = len(doc)
            full_text_parts = []
            successful_pages = 0

            logger.info(f"📄 총 {total_pages}페이지 OCR 처리 시작")

            for page_num in range(total_pages):
                try:
                    page = doc.load_page(page_num)

                    # 고해상도 렌더링 (zoom=3)
                    zoom = 3
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat, alpha=False)

                    img_bytes = pix.tobytes("png")
                    pil_image = Image.open(io.BytesIO(img_bytes))

                    # 한글 OCR 실행
                    page_text = self._ocr_page_optimized(pil_image, page_num + 1)

                    if page_text.strip():
                        full_text_parts.append(f"## 페이지 {page_num + 1}\n\n{page_text}")
                        successful_pages += 1
                        logger.info(f"✅ 페이지 {page_num + 1}/{total_pages} OCR 완료 ({len(page_text)} 문자)")
                    else:
                        logger.warning(f"⚪ 페이지 {page_num + 1}/{total_pages} OCR 결과 없음")

                    pix = None

                except Exception as page_error:
                    logger.error(f"❌ 페이지 {page_num + 1} OCR 실패: {page_error}")
                    continue

            doc.close()

            full_text = "\n\n".join(full_text_parts)

            # Markdown 파일 저장
            md_file_path = self._save_markdown(file_path, full_text, successful_pages, total_pages)

            metadata = DocumentMetadata(
                title=file_path.stem,
                page_count=total_pages,
                word_count=len(full_text.split()),
                file_size=file_path.stat().st_size,
                mime_type='application/pdf',
                parser_name=self.parser_name,
                parser_version="1.0+FullPageOCR"
            )
            metadata.has_ocr = True
            metadata.ocr_pages_processed = successful_pages

            logger.info(f"🎉 전체 페이지 OCR 완료: {successful_pages}/{total_pages}페이지, {len(full_text):,} 문자")

            return ParseResult(
                text=full_text,
                metadata=metadata,
                success=True,
                parser_name=self.parser_name,
                md_file_path=md_file_path
            )

        except Exception as e:
            logger.error(f"전체 페이지 OCR 실패: {e}", exc_info=True)
            return ParseResult(
                text="",
                metadata=None,
                success=False,
                error_message=str(e),
                parser_name=self.parser_name
            )

    def _ocr_page_optimized(self, pil_image: Image.Image, page_num: int) -> str:
        """페이지 전체 OCR (엔진 선택 가능)"""
        try:
            # Tesseract 전용 모드
            if self.ocr_engine == "tesseract":
                return self._ocr_with_tesseract(pil_image, page_num)

            # EasyOCR 전용 모드
            elif self.ocr_engine == "easyocr":
                if self.easyocr_reader is not None:
                    return self._ocr_with_easyocr(pil_image, page_num)
                else:
                    logger.warning("EasyOCR 전용 모드이나 Reader 없음, Tesseract로 폴백")
                    return self._ocr_with_tesseract(pil_image, page_num)

            # Auto 모드 (기본값): EasyOCR 우선, 실패 시 Tesseract 폴백
            else:
                if self.easyocr_reader is not None:
                    return self._ocr_with_easyocr(pil_image, page_num)
                else:
                    return self._ocr_with_tesseract(pil_image, page_num)

        except Exception as e:
            logger.error(f"페이지 {page_num} OCR 실패: {e}")
            return ""

    def _ocr_with_easyocr(self, pil_image: Image.Image, page_num: int) -> str:
        """EasyOCR로 페이지 OCR (한글+영문 혼합 최적화 + 표 구조 보존)"""
        try:
            img_array = np.array(pil_image)

            # EasyOCR 실행 (디테일 모드로 정확도 향상)
            results = self.easyocr_reader.readtext(
                img_array,
                detail=1,  # 좌표 및 신뢰도 포함
                paragraph=False,  # 줄 단위 인식
                decoder='greedy',  # 빠른 디코딩
                beamWidth=5,  # 빔 서치 폭
                batch_size=1
            )

            # 표 구조 감지 및 변환
            table_text = self._detect_and_format_tables(results)

            cleaned = self._clean_ocr_text(table_text)

            logger.info(f"✅ EasyOCR: 페이지 {page_num} 처리 완료 ({len(results)}개 영역, {len(cleaned)}자)")
            return cleaned

        except Exception as e:
            logger.warning(f"⚠️ EasyOCR 실패 (페이지 {page_num}), Tesseract로 폴백: {e}")
            return self._ocr_with_tesseract(pil_image, page_num)

    def _ocr_with_tesseract(self, pil_image: Image.Image, page_num: int) -> str:
        """Tesseract로 페이지 OCR (한글+영문 혼합, 고급 전처리)"""
        try:
            img_array = np.array(pil_image)

            # 그레이스케일 변환
            if len(img_array.shape) == 3:
                img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                img_gray = img_array

            # 고급 전처리
            # 1. 대비 향상 (CLAHE)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(img_gray)

            # 2. 노이즈 제거
            denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

            # 3. 샤프닝
            kernel_sharpen = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)

            # 4. 적응형 이진화
            thresh = cv2.adaptiveThreshold(
                sharpened, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 15, 3
            )

            # 5. Tesseract OCR
            custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1 -c textord_min_linesize=2.5'
            ocr_text = pytesseract.image_to_string(
                thresh, lang='kor+eng', config=custom_config
            )

            cleaned = self._clean_ocr_text(ocr_text)
            logger.info(f"✅ Tesseract: 페이지 {page_num} 처리 완료 ({len(cleaned)}자)")
            return cleaned

        except Exception as e:
            logger.error(f"❌ Tesseract OCR 실패 (페이지 {page_num}): {e}")
            return ""

    def _detect_and_format_tables(self, ocr_results: list) -> str:
        """OCR 결과에서 표 구조 감지 및 Markdown 테이블로 변환"""
        if not ocr_results:
            return ""

        # 신뢰도 필터링 및 좌표 추출
        filtered_results = []
        for bbox, text, confidence in ocr_results:
            if confidence > 0.3:
                # bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                x_coords = [pt[0] for pt in bbox]
                y_coords = [pt[1] for pt in bbox]
                x_min, x_max = min(x_coords), max(x_coords)
                y_min, y_max = min(y_coords), max(y_coords)
                x_center = (x_min + x_max) / 2
                y_center = (y_min + y_max) / 2

                filtered_results.append({
                    'text': text,
                    'x_min': x_min,
                    'x_max': x_max,
                    'y_min': y_min,
                    'y_max': y_max,
                    'x_center': x_center,
                    'y_center': y_center,
                    'width': x_max - x_min,
                    'height': y_max - y_min
                })

        if not filtered_results:
            return ""

        # Y좌표로 행 그룹화 (같은 행에 있는 텍스트들)
        rows = []
        current_row = []
        y_threshold = 15  # Y좌표 차이 임계값

        sorted_by_y = sorted(filtered_results, key=lambda x: x['y_center'])

        for item in sorted_by_y:
            if not current_row:
                current_row.append(item)
            else:
                # 같은 행인지 확인
                avg_y = sum(r['y_center'] for r in current_row) / len(current_row)
                if abs(item['y_center'] - avg_y) < y_threshold:
                    current_row.append(item)
                else:
                    # 새로운 행 시작
                    rows.append(sorted(current_row, key=lambda x: x['x_center']))
                    current_row = [item]

        if current_row:
            rows.append(sorted(current_row, key=lambda x: x['x_center']))

        # 표 감지: 연속된 행들이 비슷한 열 구조를 가지는지 확인
        output_lines = []
        table_buffer = []

        for row in rows:
            # 현재 행이 표의 일부인지 판단
            if len(row) >= 2 and self._is_table_row(row, table_buffer):
                table_buffer.append(row)
            else:
                # 표 버퍼가 있으면 Markdown 테이블로 변환
                if len(table_buffer) >= 2:
                    table_md = self._format_as_markdown_table(table_buffer)
                    output_lines.append(table_md)
                    output_lines.append("")

                # 일반 텍스트 추가
                table_buffer = []
                row_text = ' '.join([item['text'] for item in row])
                output_lines.append(row_text)

        # 마지막 표 처리
        if len(table_buffer) >= 2:
            table_md = self._format_as_markdown_table(table_buffer)
            output_lines.append(table_md)

        return '\n'.join(output_lines)

    def _is_table_row(self, row: list, table_buffer: list) -> bool:
        """현재 행이 표의 일부인지 판단"""
        if not table_buffer:
            return len(row) >= 2

        # 열 개수가 비슷한지 확인
        avg_cols = sum(len(r) for r in table_buffer) / len(table_buffer)
        if abs(len(row) - avg_cols) > 2:
            return False

        return True

    def _format_as_markdown_table(self, table_rows: list) -> str:
        """표 데이터를 Markdown 테이블로 포맷팅"""
        if not table_rows:
            return ""

        # 최대 열 개수 결정
        max_cols = max(len(row) for row in table_rows)

        # 각 행을 열 개수에 맞춰 정규화
        normalized_rows = []
        for row in table_rows:
            cells = [item['text'] for item in row]
            # 부족한 열은 빈 문자열로 채움
            while len(cells) < max_cols:
                cells.append('')
            normalized_rows.append(cells)

        # Markdown 테이블 생성
        lines = []

        # 첫 행을 헤더로 사용
        if normalized_rows:
            header = '| ' + ' | '.join(normalized_rows[0]) + ' |'
            lines.append(header)
            lines.append('|' + '---|' * max_cols)

            # 나머지 행들
            for row in normalized_rows[1:]:
                row_line = '| ' + ' | '.join(row) + ' |'
                lines.append(row_line)

        return '\n'.join(lines)

    def _clean_ocr_text(self, text: str) -> str:
        """OCR 결과 텍스트 정리"""
        if not text:
            return ""

        import re
        # 연속 공백 제거
        cleaned = re.sub(r' +', ' ', text)
        # 연속 줄바꿈 정리 (테이블 구분은 유지)
        cleaned = re.sub(r'\n{4,}', '\n\n', cleaned)
        # 각 줄 공백 제거 (테이블 라인은 제외)
        lines = []
        for line in cleaned.split('\n'):
            if line.strip().startswith('|'):
                lines.append(line)  # 테이블 라인은 그대로 유지
            else:
                lines.append(line.strip())
        cleaned = '\n'.join(lines)
        return cleaned.strip()

    def _save_markdown(self, file_path: Path, content: str, successful_pages: int, total_pages: int) -> str:
        """Markdown 파일 저장"""
        try:
            output_dir = file_path.parent / file_path.stem
            output_dir.mkdir(exist_ok=True)

            md_file_path = output_dir / "docling_ocr.md"

            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {file_path.stem}\n\n")
                f.write(f"**파서:** Docling + OCR (전체 페이지)\n")
                f.write(f"**생성일시:** {self._get_current_time()}\n")
                f.write(f"**원본파일:** {file_path.name}\n")
                f.write(f"**OCR 처리:** {successful_pages}/{total_pages} 페이지 성공\n")
                f.write(f"**텍스트 길이:** {len(content):,} 문자\n\n")
                f.write("---\n\n")
                f.write(content)

            logger.info(f"📝 Markdown 저장 완료: {md_file_path}")
            return str(md_file_path)

        except Exception as e:
            logger.warning(f"Markdown 저장 실패: {e}")
            return None

    def _docling_only_parse(self, file_path: Path) -> ParseResult:
        """OCR 없이 Docling만 사용 (폴백)"""
        from .docling_parser import DoclingParser
        parser = DoclingParser()
        return parser.parse(file_path)

    def _get_current_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")