"""
Docling + PyMuPDF 블록 단위 하이브리드 파서
- Docling: 구조 분석 (테이블, 섹션, 헤더)
- PyMuPDF: CID가 깨진 블록의 텍스트 교체
"""

from pathlib import Path
from typing import Optional, Dict, List, Tuple
import logging
import re
from difflib import SequenceMatcher

from .base import DocumentParser, ParseResult, DocumentMetadata
from .docling_parser import DoclingParser
from .pdf_parser import PdfParser
from .docling_ocr_parser import DoclingOCRParser

logger = logging.getLogger(__name__)


class DoclingHybridParser(DocumentParser):
    """
    Docling과 PyMuPDF를 결합한 블록 단위 하이브리드 파서

    작동 방식:
    1. Docling으로 전체 문서 파싱 (구조 우선: 헤더, 테이블, 섹션)
    2. 마크다운을 블록 단위로 분해 (헤더, 문단, 테이블 등)
    3. 각 블록별로 CID 패턴 검사
    4. CID가 있는 텍스트 블록만 PyMuPDF 텍스트로 교체
    5. 구조는 Docling, 깨끗한 텍스트는 PyMuPDF
    """

    def __init__(self, ocr_engine: str = "auto"):
        super().__init__("docling_hybrid")
        self.supported_extensions = ['.pdf']
        self.supported_mime_types = ['application/pdf']
        self.docling_parser = DoclingParser()
        self.pymupdf_parser = PdfParser()
        self.docling_ocr_parser = DoclingOCRParser(ocr_engine=ocr_engine)
        self.cid_pattern = re.compile(r'/_\d+')

    def _has_cid_issues(self, text: str, threshold: float = 0.05) -> bool:
        """텍스트에 CID 인코딩 문제가 있는지 검사

        Args:
            text: 검사할 텍스트
            threshold: CID 비율 임계값 (기본 5%)

        Returns:
            True if CID 패턴이 threshold 이상 발견됨
        """
        if not text or len(text) < 10:
            return False

        cid_matches = self.cid_pattern.findall(text)
        if not cid_matches:
            return False

        # CID 패턴 개수 / 단어 수
        word_count = max(len(text.split()), 1)
        cid_ratio = len(cid_matches) / word_count

        return cid_ratio > threshold

    def _split_into_blocks(self, markdown: str) -> List[Dict[str, str]]:
        """마크다운을 블록 단위로 분해

        블록 타입:
        - header: # 제목
        - table: | 테이블 |
        - paragraph: 일반 문단
        - empty: 빈 줄

        Returns:
            블록 정보 리스트 [{"type": "header", "content": "...", "has_cid": bool}, ...]
        """
        blocks = []
        current_block = {"type": "paragraph", "lines": []}
        in_table = False

        for line in markdown.split('\n'):
            # 헤더 감지
            if line.startswith('#'):
                # 이전 블록 저장
                if current_block["lines"]:
                    content = '\n'.join(current_block["lines"])
                    blocks.append({
                        "type": current_block["type"],
                        "content": content,
                        "has_cid": self._has_cid_issues(content)
                    })
                    current_block = {"type": "paragraph", "lines": []}

                # 헤더 블록 추가
                blocks.append({
                    "type": "header",
                    "content": line,
                    "has_cid": self._has_cid_issues(line)
                })
                in_table = False
                continue

            # 테이블 감지
            if line.strip().startswith('|'):
                if not in_table:
                    # 이전 블록 저장
                    if current_block["lines"]:
                        content = '\n'.join(current_block["lines"])
                        blocks.append({
                            "type": current_block["type"],
                            "content": content,
                            "has_cid": self._has_cid_issues(content)
                        })
                    current_block = {"type": "table", "lines": []}
                    in_table = True

                current_block["lines"].append(line)
                continue

            # 테이블 종료
            if in_table and not line.strip().startswith('|'):
                if current_block["lines"]:
                    content = '\n'.join(current_block["lines"])
                    blocks.append({
                        "type": current_block["type"],
                        "content": content,
                        "has_cid": self._has_cid_issues(content)
                    })
                current_block = {"type": "paragraph", "lines": []}
                in_table = False

            # 빈 줄
            if not line.strip():
                if current_block["lines"]:
                    content = '\n'.join(current_block["lines"])
                    blocks.append({
                        "type": current_block["type"],
                        "content": content,
                        "has_cid": self._has_cid_issues(content)
                    })
                    current_block = {"type": "paragraph", "lines": []}

                blocks.append({"type": "empty", "content": "", "has_cid": False})
                continue

            # 일반 문단
            current_block["lines"].append(line)

        # 마지막 블록 저장
        if current_block["lines"]:
            content = '\n'.join(current_block["lines"])
            blocks.append({
                "type": current_block["type"],
                "content": content,
                "has_cid": self._has_cid_issues(content)
            })

        return blocks

    def _find_best_match_in_pymupdf(self, cid_text: str, pymupdf_text: str, context_size: int = 50) -> Optional[str]:
        """PyMuPDF 텍스트에서 CID 텍스트와 가장 일치하는 부분 찾기

        전략:
        1. CID 패턴을 제거한 순수 텍스트로 유사도 계산
        2. 가장 유사한 부분을 PyMuPDF 텍스트에서 찾아서 반환

        Args:
            cid_text: CID가 포함된 원본 텍스트
            pymupdf_text: PyMuPDF로 추출한 전체 텍스트
            context_size: 검색할 최소 문자 수

        Returns:
            교체할 텍스트 또는 None
        """
        # CID 패턴 제거한 순수 텍스트 추출
        clean_text = self.cid_pattern.sub('', cid_text).strip()

        # 너무 짧으면 매칭 불가
        if len(clean_text) < 10:
            return None

        # 단어 기반으로 검색
        words = [w for w in clean_text.split() if len(w) > 2]  # 2글자 이상 단어만
        if len(words) < 3:
            return None

        # PyMuPDF 텍스트에서 가장 많은 단어가 연속으로 나타나는 부분 찾기
        best_match = None
        best_score = 0

        # 슬라이딩 윈도우로 검색
        pymupdf_words = pymupdf_text.split()
        window_size = min(len(words) * 2, 100)  # 원본의 2배 크기 윈도우

        for i in range(len(pymupdf_words) - window_size + 1):
            window = ' '.join(pymupdf_words[i:i+window_size])

            # 유사도 계산
            matcher = SequenceMatcher(None, clean_text.lower(), window.lower())
            score = matcher.ratio()

            if score > best_score:
                best_score = score
                best_match = window

        # 유사도가 30% 이상일 때만 교체
        if best_score > 0.3:
            logger.debug(f"✓ 매칭 발견 (유사도: {best_score:.2%})")
            return best_match

        return None

    def _replace_cid_blocks(self, blocks: List[Dict], pymupdf_text: str) -> str:
        """CID가 있는 블록을 PyMuPDF 텍스트로 교체

        Args:
            blocks: Docling 블록 리스트
            pymupdf_text: PyMuPDF 전체 텍스트

        Returns:
            교체된 최종 마크다운
        """
        result_lines = []
        replaced_count = 0

        for block in blocks:
            # 헤더와 테이블은 항상 유지 (구조 정보이므로)
            if block["type"] in ["header", "table", "empty"]:
                result_lines.append(block["content"])
                continue

            # 문단 블록 처리
            if block["has_cid"]:
                # PyMuPDF에서 매칭되는 텍스트 찾기
                replacement = self._find_best_match_in_pymupdf(block["content"], pymupdf_text)

                if replacement:
                    result_lines.append(replacement)
                    replaced_count += 1
                    logger.debug(f"🔧 블록 교체됨 (길이: {len(block['content'])} → {len(replacement)})")
                else:
                    # 매칭 실패하면 원본 유지
                    result_lines.append(block["content"])
                    logger.debug(f"⚠️ 매칭 실패, 원본 유지")
            else:
                # CID 없으면 원본 유지
                result_lines.append(block["content"])

        logger.info(f"✅ 블록 교체 완료: {replaced_count}개 블록 수정됨")
        return '\n'.join(result_lines)

    def parse(self, file_path: Path) -> ParseResult:
        """블록 단위 하이브리드 파싱 실행"""
        try:
            logger.info(f"🔀 블록 단위 하이브리드 파서 시작: {file_path.name}")

            # 1. Docling으로 전체 파싱 (구조 우선)
            logger.info("📚 Phase 1: Docling으로 구조 분석")
            docling_result = self.docling_parser.parse(file_path)

            if not docling_result.success:
                logger.warning("Docling 파싱 실패, PyMuPDF 전용 모드로 전환")
                return self.pymupdf_parser.parse(file_path)

            # 2. 전체 텍스트에서 CID 문제 검사
            has_cid = self._has_cid_issues(docling_result.text)

            if not has_cid:
                logger.info("✅ CID 문제 없음, Docling 결과 사용")
                docling_result.parser_name = self.parser_name
                return docling_result

            logger.info("⚠️ CID 인코딩 문제 감지, 블록 단위 하이브리드 활성화")

            # 3. 여러 파서 시도하여 가장 깨끗한 텍스트 찾기
            clean_text_source = None

            # 3-1. PyMuPDF 시도
            logger.info("📖 Phase 2: PyMuPDF로 텍스트 추출")
            pymupdf_result = self.pymupdf_parser.parse(file_path)

            if pymupdf_result.success and not self._has_cid_issues(pymupdf_result.text):
                logger.info("✅ PyMuPDF 텍스트 깨끗함")
                clean_text_source = pymupdf_result.text
            else:
                logger.warning("⚠️ PyMuPDF도 CID 문제 있음, OCR 시도")

                # 3-2. OCR 시도
                logger.info("📖 Phase 2-2: Docling OCR로 텍스트 추출")
                ocr_result = self.docling_ocr_parser.parse(file_path)

                if ocr_result.success and not self._has_cid_issues(ocr_result.text):
                    logger.info("✅ OCR 텍스트 깨끗함")
                    clean_text_source = ocr_result.text
                elif ocr_result.success:
                    # OCR이 PyMuPDF보다 나은지 확인 (CID 비율 비교)
                    pymupdf_cid_count = len(self.cid_pattern.findall(pymupdf_result.text)) if pymupdf_result.success else float('inf')
                    ocr_cid_count = len(self.cid_pattern.findall(ocr_result.text))

                    if ocr_cid_count < pymupdf_cid_count:
                        logger.info(f"✅ OCR이 더 나음 (CID: {ocr_cid_count} vs {pymupdf_cid_count})")
                        clean_text_source = ocr_result.text
                    else:
                        logger.info(f"⚠️ PyMuPDF 사용 (CID: {pymupdf_cid_count} vs {ocr_cid_count})")
                        clean_text_source = pymupdf_result.text if pymupdf_result.success else None
                else:
                    logger.warning("OCR 추출 실패")
                    clean_text_source = pymupdf_result.text if pymupdf_result.success else None

            # 깨끗한 텍스트를 찾지 못하면 원본 사용
            if not clean_text_source:
                logger.warning("⚠️ 깨끗한 텍스트 소스 없음, Docling 원본 사용")
                return docling_result

            # 4. 블록 단위 분해
            logger.info("🧩 Phase 3: 블록 단위 분해 및 CID 검사")
            blocks = self._split_into_blocks(docling_result.text)

            cid_block_count = sum(1 for b in blocks if b.get("has_cid", False))
            logger.info(f"총 {len(blocks)}개 블록 중 {cid_block_count}개 블록에 CID 문제 발견")

            # 5. CID 블록 교체
            logger.info("🔧 Phase 4: CID 블록을 깨끗한 텍스트로 교체")
            final_text = self._replace_cid_blocks(blocks, clean_text_source)

            # 6. 최종 검증
            remaining_cid = self._has_cid_issues(final_text)
            if remaining_cid:
                logger.warning("⚠️ 일부 CID 패턴이 남아있음")
            else:
                logger.info("✅ 모든 CID 패턴 제거 완료")

            # 메타데이터 업데이트
            if docling_result.metadata:
                docling_result.metadata.parser_name = self.parser_name
                docling_result.metadata.parser_version = "1.0+BlockHybrid"

            return ParseResult(
                success=True,
                text=final_text,
                metadata=docling_result.metadata,
                parser_name=self.parser_name
            )

        except Exception as e:
            logger.error(f"블록 하이브리드 파서 오류: {e}")
            return ParseResult(
                success=False,
                text="",
                metadata=None,
                parser_name=self.parser_name,
                error_message=str(e)
            )
