import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from .base import DocumentParser, ParseResult, DocumentMetadata

class MarkdownParser(DocumentParser):
    """Markdown 파일 파서"""
    
    def __init__(self):
        super().__init__("markdown_parser")
        self.supported_extensions = ['.md', '.markdown', '.mdown', '.mkd']
        self.supported_mime_types = [
            'text/markdown',
            'text/x-markdown'
        ]
    
    def parse(self, file_path: Path) -> ParseResult:
        """Markdown 파일을 파싱합니다."""
        try:
            # 파일 기본 정보
            file_info = self.get_file_info(file_path)
            
            # 인코딩 감지 및 파일 읽기
            encoding = self._detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                markdown_content = f.read()
            
            # 메타데이터 추출 (YAML front matter)
            front_matter, content = self._extract_front_matter(markdown_content)
            
            # 마크다운에서 순수 텍스트 추출
            plain_text = self._markdown_to_text(content)
            
            # 제목 추출
            title = self._extract_title(content, front_matter, file_path)
            author = front_matter.get('author') if front_matter else None
            
            word_count = len(plain_text.split()) if plain_text else 0
            
            # 메타데이터 생성
            metadata = DocumentMetadata(
                title=title,
                author=author,
                word_count=word_count,
                file_size=file_info.get("file_size"),
                created_date=str(file_info.get("created_date", "")),
                modified_date=str(file_info.get("modified_date", "")),
                encoding=encoding,
                mime_type="text/markdown"
            )
            
            return ParseResult(
                text=plain_text,
                metadata=metadata,
                success=True,
                parser_name=self.parser_name
            )
            
        except Exception as e:
            return self.create_error_result(f"Markdown 파싱 오류: {str(e)}", file_path)
    
    def _detect_encoding(self, file_path: Path) -> str:
        """파일의 인코딩을 감지합니다."""
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
            
            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')
            
            if not encoding or result.get('confidence', 0) < 0.7:
                encoding = 'utf-8'
            
            return encoding
            
        except Exception:
            return 'utf-8'
    
    def _extract_front_matter(self, content: str) -> tuple[Optional[Dict], str]:
        """YAML front matter를 추출합니다."""
        try:
            # YAML front matter 패턴 (--- 사이의 내용)
            front_matter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
            match = re.match(front_matter_pattern, content, re.DOTALL)
            
            if match:
                yaml_content = match.group(1)
                remaining_content = content[match.end():]
                
                # 간단한 YAML 파싱 (키: 값 형태만)
                front_matter = {}
                for line in yaml_content.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        if value:
                            front_matter[key] = value
                
                return front_matter, remaining_content
            
            return None, content
            
        except Exception:
            return None, content
    
    def _markdown_to_text(self, markdown_content: str) -> str:
        """Markdown을 순수 텍스트로 변환합니다."""
        text = markdown_content
        
        # 코드 블록 제거 (```로 감싸진 부분)
        text = re.sub(r'```[\s\S]*?```', '', text)
        
        # 인라인 코드 제거 (`로 감싸진 부분)
        text = re.sub(r'`[^`]*`', '', text)
        
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # 마크다운 문법 제거
        text = re.sub(r'#+\s*', '', text)  # 헤딩
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # 볼드
        text = re.sub(r'\*([^*]+)\*', r'\1', text)  # 이탤릭
        text = re.sub(r'__([^_]+)__', r'\1', text)  # 볼드
        text = re.sub(r'_([^_]+)_', r'\1', text)  # 이탤릭
        text = re.sub(r'~~([^~]+)~~', r'\1', text)  # 취소선
        
        # 링크 제거 [텍스트](링크) -> 텍스트
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # 이미지 제거 ![alt](src)
        text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
        
        # 리스트 마커 제거
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # 인용문 제거
        text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
        
        # 수평선 제거
        text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\*{3,}$', '', text, flags=re.MULTILINE)
        
        # 연속된 공백과 줄바꿈 정리
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def _extract_title(self, content: str, front_matter: Optional[Dict], file_path: Path) -> str:
        """제목을 추출합니다."""
        # front matter에서 title 확인
        if front_matter and 'title' in front_matter:
            return front_matter['title']
        
        # 첫 번째 H1 헤딩 찾기
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
        
        # 파일명 사용
        return file_path.stem
    
    def extract_structure(self, file_path: Path) -> Dict[str, Any]:
        """Markdown 문서의 구조를 분석합니다."""
        try:
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            front_matter, markdown_content = self._extract_front_matter(content)
            
            structure = {
                "front_matter": front_matter,
                "headings": self._extract_headings(markdown_content),
                "links": self._extract_links(markdown_content),
                "images": self._extract_images(markdown_content),
                "code_blocks": self._extract_code_blocks(markdown_content),
                "tables": self._count_tables(markdown_content),
                "lists": self._count_lists(markdown_content)
            }
            
            return structure
            
        except Exception as e:
            return {"error": str(e)}
    
    def _extract_headings(self, content: str) -> List[Dict[str, Any]]:
        """헤딩을 추출합니다."""
        headings = []
        for match in re.finditer(r'^(#+)\s+(.+)$', content, re.MULTILINE):
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({
                "level": level,
                "text": text,
                "position": match.start()
            })
        return headings
    
    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """링크를 추출합니다."""
        links = []
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', content):
            links.append({
                "text": match.group(1),
                "url": match.group(2)
            })
        return links
    
    def _extract_images(self, content: str) -> List[Dict[str, str]]:
        """이미지를 추출합니다."""
        images = []
        for match in re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)', content):
            images.append({
                "alt": match.group(1),
                "src": match.group(2)
            })
        return images
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """코드 블록을 추출합니다."""
        code_blocks = []
        for match in re.finditer(r'```(\w+)?\n([\s\S]*?)```', content):
            language = match.group(1) or ""
            code = match.group(2)
            code_blocks.append({
                "language": language,
                "code": code
            })
        return code_blocks
    
    def _count_tables(self, content: str) -> int:
        """테이블 개수를 카운트합니다."""
        # 간단한 테이블 패턴 매칭 (|로 구분된 행)
        table_lines = re.findall(r'^\|.+\|$', content, re.MULTILINE)
        return len(set(table_lines)) // 2  # 헤더와 구분선을 고려
    
    def _count_lists(self, content: str) -> Dict[str, int]:
        """리스트 개수를 카운트합니다."""
        unordered = len(re.findall(r'^\s*[-*+]\s+', content, re.MULTILINE))
        ordered = len(re.findall(r'^\s*\d+\.\s+', content, re.MULTILINE))
        
        return {
            "unordered": unordered,
            "ordered": ordered,
            "total": unordered + ordered
        }