from pathlib import Path
from typing import Optional, Dict, Any
from .base import DocumentParser, ParseResult, DocumentMetadata

class HtmlParser(DocumentParser):
    """HTML 파일 파서 (BeautifulSoup 사용)"""
    
    def __init__(self):
        super().__init__("html_parser")
        self.supported_extensions = ['.html', '.htm', '.xhtml']
        self.supported_mime_types = [
            'text/html',
            'application/xhtml+xml',
            'text/xhtml'
        ]
    
    def parse(self, file_path: Path) -> ParseResult:
        """HTML 파일을 파싱합니다."""
        try:
            # BeautifulSoup 임포트 확인
            try:
                from bs4 import BeautifulSoup
            except ImportError:
                return self.create_error_result(
                    "beautifulsoup4 라이브러리가 설치되지 않았습니다. 'pip install beautifulsoup4' 실행이 필요합니다.",
                    file_path
                )
            
            # 파일 기본 정보
            file_info = self.get_file_info(file_path)
            
            # HTML 파일 읽기 (인코딩 감지)
            encoding = self._detect_encoding(file_path)
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                html_content = f.read()
            
            # BeautifulSoup으로 파싱
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 메타데이터 추출
            title = self._extract_title(soup, file_path)
            author = self._extract_author(soup)
            
            # 스크립트와 스타일 태그 제거
            for script in soup(["script", "style"]):
                script.decompose()
            
            # 텍스트 추출
            text = soup.get_text()
            
            # 텍스트 정리 (연속된 공백과 줄바꿈 정리)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            word_count = len(clean_text.split()) if clean_text else 0
            
            # 메타데이터 생성
            metadata = DocumentMetadata(
                title=title,
                author=author,
                word_count=word_count,
                file_size=file_info.get("file_size"),
                created_date=str(file_info.get("created_date", "")),
                modified_date=str(file_info.get("modified_date", "")),
                encoding=encoding,
                mime_type="text/html"
            )
            
            return ParseResult(
                text=clean_text,
                metadata=metadata,
                success=True,
                parser_name=self.parser_name
            )
            
        except Exception as e:
            return self.create_error_result(f"HTML 파싱 오류: {str(e)}", file_path)
    
    def _detect_encoding(self, file_path: Path) -> str:
        """HTML 파일의 인코딩을 감지합니다."""
        try:
            # 먼저 chardet로 감지
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read(10000)
            result = chardet.detect(raw_data)
            detected_encoding = result.get('encoding', 'utf-8')
            
            # HTML 메타 태그에서 인코딩 확인
            try:
                from bs4 import BeautifulSoup
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                # charset 정보 찾기
                soup = BeautifulSoup(content, 'html.parser')
                meta_charset = soup.find('meta', charset=True)
                if meta_charset:
                    return meta_charset['charset']
                
                # http-equiv content-type에서 찾기
                meta_content_type = soup.find('meta', {'http-equiv': 'Content-Type'})
                if meta_content_type and 'content' in meta_content_type.attrs:
                    content_attr = meta_content_type['content']
                    if 'charset=' in content_attr:
                        charset = content_attr.split('charset=')[-1].strip()
                        return charset
                
            except Exception:
                pass
            
            return detected_encoding or 'utf-8'
            
        except Exception:
            return 'utf-8'
    
    def _extract_title(self, soup, file_path: Path) -> str:
        """HTML에서 제목을 추출합니다."""
        try:
            # <title> 태그에서 추출
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                return title_tag.string.strip()
            
            # <h1> 태그에서 추출
            h1_tag = soup.find('h1')
            if h1_tag:
                return h1_tag.get_text().strip()
            
            # 메타 태그에서 추출
            meta_title = soup.find('meta', {'property': 'og:title'})
            if meta_title and meta_title.get('content'):
                return meta_title['content'].strip()
            
            # 파일명 사용
            return file_path.stem
            
        except Exception:
            return file_path.stem
    
    def _extract_author(self, soup) -> Optional[str]:
        """HTML에서 저자 정보를 추출합니다."""
        try:
            # 메타 태그에서 추출
            meta_author = soup.find('meta', {'name': 'author'})
            if meta_author and meta_author.get('content'):
                return meta_author['content'].strip()
            
            # OpenGraph 메타 태그
            og_author = soup.find('meta', {'property': 'article:author'})
            if og_author and og_author.get('content'):
                return og_author['content'].strip()
            
            return None
            
        except Exception:
            return None
    
    def extract_links(self, file_path: Path) -> Dict[str, Any]:
        """HTML 파일에서 링크 정보를 추출합니다."""
        try:
            from bs4 import BeautifulSoup
            
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            links_info = {
                "internal_links": [],
                "external_links": [],
                "email_links": [],
                "total_links": 0
            }
            
            # 모든 링크 찾기
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                text = link.get_text().strip()
                
                link_data = {
                    "url": href,
                    "text": text,
                    "title": link.get('title', '')
                }
                
                if href.startswith('mailto:'):
                    links_info["email_links"].append(link_data)
                elif href.startswith('http://') or href.startswith('https://'):
                    links_info["external_links"].append(link_data)
                else:
                    links_info["internal_links"].append(link_data)
            
            links_info["total_links"] = len(links)
            return links_info
            
        except Exception as e:
            return {"error": str(e)}
    
    def extract_structure(self, file_path: Path) -> Dict[str, Any]:
        """HTML 문서의 구조 정보를 추출합니다."""
        try:
            from bs4 import BeautifulSoup
            
            encoding = self._detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            structure = {
                "headings": {},
                "images": len(soup.find_all('img')),
                "tables": len(soup.find_all('table')),
                "forms": len(soup.find_all('form')),
                "lists": len(soup.find_all(['ul', 'ol'])),
                "paragraphs": len(soup.find_all('p'))
            }
            
            # 헤딩 태그 카운트
            for i in range(1, 7):
                headings = soup.find_all(f'h{i}')
                if headings:
                    structure["headings"][f"h{i}"] = len(headings)
            
            return structure
            
        except Exception as e:
            return {"error": str(e)}