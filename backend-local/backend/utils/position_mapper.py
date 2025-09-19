from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

class PositionMapper:
    """문자 위치를 페이지/줄 번호로 변환하는 유틸리티"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def create_position_map(self, text: str, file_path: Optional[Path] = None) -> Dict[str, any]:
        """
        텍스트에서 위치 매핑 정보를 생성합니다.
        
        Args:
            text: 전체 텍스트
            file_path: 원본 파일 경로 (PDF인 경우 페이지 정보 추출용)
            
        Returns:
            Dict: 위치 매핑 정보
        """
        position_map = {
            'char_to_line': {},
            'line_starts': [],
            'page_breaks': [],
            'total_lines': 0,
            'total_pages': 1
        }
        
        # 줄별 위치 매핑 - 개선된 방법
        lines = text.split('\n')
        char_position = 0
        
        for line_idx, line in enumerate(lines):
            position_map['line_starts'].append(char_position)
            
            # 현재 줄의 모든 문자에 대해 줄 번호 매핑
            line_length = len(line)
            for char_idx in range(line_length):
                position_map['char_to_line'][char_position + char_idx] = line_idx + 1
            
            # 개행 문자 위치도 현재 줄에 속한다고 간주
            if line_idx < len(lines) - 1:  # 마지막 줄이 아닌 경우에만
                position_map['char_to_line'][char_position + line_length] = line_idx + 1
            
            char_position += line_length + 1  # +1 for newline
        
        position_map['total_lines'] = len(lines)
        
        # PDF 파일인 경우 페이지 정보 추출
        if file_path and file_path.suffix.lower() == '.pdf':
            page_info = self._extract_pdf_page_info(file_path, text)
            position_map.update(page_info)
        else:
            # 페이지 구분 추정 (긴 공백이나 특정 패턴으로)
            page_info = self._estimate_page_breaks(text)
            position_map.update(page_info)
            
        return position_map
    
    def get_position_info(self, char_pos: int, position_map: Dict[str, any]) -> Tuple[int, int, int]:
        """
        문자 위치에서 페이지/줄/컬럼 번호를 반환합니다.
        
        Args:
            char_pos: 문자 위치
            position_map: 위치 매핑 정보
            
        Returns:
            Tuple[int, int, int]: (페이지 번호, 줄 번호, 컬럼 번호)
        """
        # 줄 번호 찾기 - 개선된 방법
        line_number = self._find_line_number(char_pos, position_map)
        
        # 페이지 번호 찾기
        page_number = 1
        for page_break in position_map['page_breaks']:
            if char_pos >= page_break:
                page_number += 1
            else:
                break
        
        # 컬럼 번호 계산
        column_number = 1
        if line_number > 0 and line_number <= len(position_map['line_starts']):
            line_start = position_map['line_starts'][line_number - 1]
            column_number = char_pos - line_start + 1
            
        return page_number, line_number, column_number
    
    def _find_line_number(self, char_pos: int, position_map: Dict[str, any]) -> int:
        """문자 위치에서 줄 번호를 찾습니다."""
        # char_to_line 매핑에서 먼저 확인
        if char_pos in position_map['char_to_line']:
            line_num = position_map['char_to_line'][char_pos]
            self.logger.debug(f"📍 직접 매핑으로 찾은 줄 번호: 위치 {char_pos} -> 줄 {line_num}")
            return line_num
        
        # line_starts를 사용하여 이진 탐색으로 줄 번호 찾기
        line_starts = position_map['line_starts']
        if not line_starts:
            self.logger.warning(f"⚠️ line_starts가 비어있음, 위치 {char_pos}를 줄 1로 설정")
            return 1
            
        # 해당 문자 위치가 속한 줄 찾기
        for i in range(len(line_starts) - 1, -1, -1):
            if char_pos >= line_starts[i]:
                line_num = i + 1
                self.logger.debug(f"📍 이진 탐색으로 찾은 줄 번호: 위치 {char_pos} -> 줄 {line_num} (line_start: {line_starts[i]})")
                return line_num
                
        self.logger.warning(f"⚠️ 위치 {char_pos}에 해당하는 줄을 찾지 못함, 줄 1로 설정")
        return 1
    
    def _extract_pdf_page_info(self, file_path: Path, text: str) -> Dict[str, any]:
        """PDF 파일에서 페이지 정보를 추출합니다."""
        page_info = {
            'page_breaks': [],
            'total_pages': 1
        }
        
        try:
            import fitz
            doc = fitz.open(str(file_path))
            
            page_info['total_pages'] = doc.page_count
            char_position = 0
            
            # 각 페이지의 텍스트 길이를 계산하여 페이지 구분점 찾기
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                
                if page_num > 0:  # 첫 페이지가 아닌 경우
                    page_info['page_breaks'].append(char_position)
                
                char_position += len(page_text) + 2  # +2 for page separator
            
            doc.close()
            
        except Exception as e:
            self.logger.warning(f"PDF 페이지 정보 추출 실패: {e}")
            # Fallback: 텍스트 기반 페이지 추정
            page_info = self._estimate_page_breaks(text)
            
        return page_info
    
    def _estimate_page_breaks(self, text: str) -> Dict[str, any]:
        """텍스트에서 페이지 구분을 추정합니다."""
        import re
        
        page_info = {
            'page_breaks': [],
            'total_pages': 1
        }
        
        # 페이지 구분 패턴들
        page_break_patterns = [
            r'\f',  # Form feed 문자 (가장 확실한 페이지 구분)
            r'\n\s*\n\s*\n\s*\n',  # 연속된 빈 줄 4개 이상
            r'페이지\s*\d+',  # "페이지 N" 패턴
            r'Page\s*\d+',  # "Page N" 패턴
            r'\n\s*-\s*\d+\s*-\s*\n',  # "- 숫자 -" 패턴
            r'\n\s*=+\s*\n',  # "========" 패턴
            r'\n\s*#{3,}\s*\n',  # "### 제목 ###" 패턴 (Markdown)
        ]
        
        # 패턴 기반 페이지 구분점 찾기
        for pattern in page_break_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                page_break_pos = match.start()
                if page_break_pos not in page_info['page_breaks']:
                    page_info['page_breaks'].append(page_break_pos)
        
        # 패턴으로 찾은 페이지 구분점이 없거나 너무 적으면 길이 기반으로 추정
        if len(page_info['page_breaks']) == 0:
            # 텍스트 길이 기반 페이지 구분 (대략 3000자당 1페이지로 추정)
            chars_per_page = 3000
            text_length = len(text)
            
            if text_length > chars_per_page:
                estimated_pages = min(text_length // chars_per_page, 10)  # 최대 10페이지로 제한
                
                # 문단 구분점을 찾아서 페이지 구분점으로 사용
                paragraph_breaks = []
                lines = text.split('\n')
                char_pos = 0
                
                for i, line in enumerate(lines):
                    if char_pos > chars_per_page and len(paragraph_breaks) < estimated_pages - 1:
                        # 빈 줄이거나 짧은 줄에서 페이지 구분
                        if not line.strip() or len(line.strip()) < 20:
                            paragraph_breaks.append(char_pos)
                            chars_per_page += 3000  # 다음 페이지 구분점 계산
                    
                    char_pos += len(line) + 1  # +1 for newline
                
                page_info['page_breaks'].extend(paragraph_breaks)
        
        # 페이지 구분점 정렬
        page_info['page_breaks'].sort()
        page_info['total_pages'] = len(page_info['page_breaks']) + 1
        
        # 너무 많은 페이지로 분할되지 않도록 제한
        if page_info['total_pages'] > 20:
            # 상위 19개만 유지 (최대 20페이지)
            page_info['page_breaks'] = page_info['page_breaks'][:19]
            page_info['total_pages'] = 20
        
        return page_info
    
    def format_position(self, page_number: int, line_number: int, column_number: int = None) -> str:
        """페이지/줄/컬럼 번호를 포맷팅합니다."""
        if column_number:
            return f"페이지 {page_number}, 줄 {line_number}, 컬럼 {column_number}"
        else:
            return f"페이지 {page_number}, 줄 {line_number}"