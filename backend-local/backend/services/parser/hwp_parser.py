import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from .base import DocumentParser, ParseResult, DocumentMetadata
from utils.text_cleaner import TextCleaner

class HwpParser(DocumentParser):
    """HWP(한글 워드프로세서) 파일 파서
    
    pyhwp 라이브러리를 사용하여 HWP 파일에서 텍스트를 추출합니다.
    """
    
    def __init__(self):
        super().__init__("hwp_parser")
        self.supported_extensions = ['.hwp']
        self.supported_mime_types = [
            'application/x-hwp',
            'application/vnd.hancom.hwp',
            'application/haansofthwp'
        ]
        
        # HWP 파싱을 위한 기본 설정
        self.hwp5_available = False  # 현재는 라이브러리 호환성 문제로 비활성화
    
    def parse(self, file_path: Path) -> ParseResult:
        """HWP 파일을 파싱하여 텍스트와 메타데이터를 추출합니다."""
        if not self.hwp5_available:
            # HWP 파일 기본 처리 - 메타데이터만 추출하고 플레이스홀더 텍스트 제공
            try:
                file_info = self.get_file_info(file_path)
                
                # 기본 플레이스홀더 텍스트
                text = f"HWP 파일 '{file_path.name}'이 감지되었습니다.\n\n" \
                       f"파일 크기: {file_info.get('file_size', 0):,} bytes\n" \
                       f"현재 HWP 파일의 텍스트 추출 기능은 개발 중입니다."
                
                # HWP 구조 정보 가져오기
                structure_info = self._analyze_hwp_structure(file_path)
                
                # 메타데이터 생성
                metadata = DocumentMetadata(
                    title=file_path.stem,
                    word_count=len(text.split()) if text else 0,
                    file_size=file_info.get("file_size"),
                    created_date=str(file_info.get("created_date", "")),
                    modified_date=str(file_info.get("modified_date", "")),
                    mime_type="application/x-hwp"
                )
                
                # 구조 정보 수동 설정
                for key, value in structure_info.items():
                    setattr(metadata, key, value)
                
                return ParseResult(
                    text=text,
                    metadata=metadata,
                    success=True,
                    parser_name=self.parser_name
                )
                
            except Exception as e:
                return self.create_error_result(f"HWP 파일 처리 오류: {str(e)}", file_path)
        
        try:
            # 파일 기본 정보
            file_info = self.get_file_info(file_path)
            
            # HWP 파일에서 텍스트 추출
            extracted_text = self._extract_text_from_hwp(file_path)
            
            # 텍스트 정제
            text = TextCleaner.clean_text(extracted_text) if extracted_text else ""
            
            # 단어 수 계산
            word_count = len(text.split()) if text else 0
            
            # HWP 파일 구조 분석
            structure_info = self._analyze_hwp_structure(file_path)
            
            # 메타데이터 생성
            metadata = DocumentMetadata(
                title=file_path.stem,
                word_count=word_count,
                file_size=file_info.get("file_size"),
                created_date=str(file_info.get("created_date", "")),
                modified_date=str(file_info.get("modified_date", "")),
                mime_type="application/x-hwp",
                **structure_info  # HWP 구조 정보 추가
            )
            
            success = bool(text and len(text.strip()) > 0)
            
            return ParseResult(
                text=text,
                metadata=metadata,
                success=success,
                parser_name=self.parser_name
            )
            
        except Exception as e:
            return self.create_error_result(f"HWP 파싱 오류: {str(e)}", file_path)
    
    def _extract_text_from_hwp(self, file_path: Path) -> str:
        """HWP 파일에서 텍스트를 추출합니다."""
        # pyhwp 라이브러리의 복잡성으로 인해 현재는 기본 메시지만 반환
        # 향후 더 나은 HWP 파싱 라이브러리가 있을 때 개선 예정
        try:
            # 명령행 도구 사용 시도
            return self._extract_text_with_cli(file_path)
        except Exception as e:
            # 기본 플레이스홀더 텍스트 반환
            return f"HWP 파일 '{file_path.name}'이 감지되었습니다. 현재 HWP 파일의 텍스트 추출 기능은 제한적입니다."
    
    def _extract_text_alternative(self, hwp_doc) -> str:
        """대안 방법으로 HWP에서 텍스트를 추출합니다."""
        import hwp5
        try:
            from hwp5.text import model_to_text
        except ImportError:
            model_to_text = None
        
        try:
            # 문서 모델을 텍스트로 변환
            texts = []
            
            if hasattr(hwp_doc, 'bodytext') and model_to_text:
                for section in hwp_doc.bodytext.sections:
                    try:
                        # 섹션 모델을 텍스트로 변환
                        section_text = model_to_text(section)
                        if section_text and section_text.strip():
                            texts.append(section_text)
                    except Exception as e:
                        continue
            
            return '\n\n'.join(texts)
            
        except Exception as e:
            return ""
    
    def _extract_text_with_cli(self, file_path: Path) -> str:
        """명령행 도구를 사용하여 텍스트를 추출합니다."""
        try:
            import subprocess
            import tempfile
            
            # 임시 파일에 텍스트 추출
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                temp_path = Path(temp_file.name)
            
            # hwp5txt 명령 실행
            result = subprocess.run(
                ['hwp5txt', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                return result.stdout
            else:
                return ""
                
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
            return ""
        except Exception as e:
            return ""
    
    def _analyze_hwp_structure(self, file_path: Path) -> Dict[str, Any]:
        """HWP 파일의 구조 정보를 분석합니다."""
        # 현재는 기본 정보만 제공
        structure_info = {
            'sections_count': 1,  # 기본값
            'pages_count': 1,     # 기본값  
            'tables_count': 0,    # 알 수 없음
            'images_count': 0,    # 알 수 없음
            'footnotes_count': 0, # 알 수 없음
            'hwp_version': 'unknown',
            'parsing_status': 'limited'  # 제한적 파싱
        }
        
        return structure_info
    
    def _count_section_objects(self, section, structure_info: Dict[str, Any]) -> None:
        """섹션 내의 개체들을 카운트합니다."""
        try:
            # 섹션의 모든 하위 요소 순회
            for item in getattr(section, 'items', []):
                item_type = type(item).__name__
                
                if 'table' in item_type.lower():
                    structure_info['tables_count'] += 1
                elif 'picture' in item_type.lower() or 'image' in item_type.lower():
                    structure_info['images_count'] += 1
                elif 'footnote' in item_type.lower():
                    structure_info['footnotes_count'] += 1
                    
        except Exception as e:
            pass
    
    def can_parse(self, file_path: Path) -> bool:
        """파일을 파싱할 수 있는지 확인합니다."""
        if not self.hwp5_available:
            return False
        
        return (
            file_path.suffix.lower() in self.supported_extensions and
            file_path.exists() and
            file_path.stat().st_size > 0
        )