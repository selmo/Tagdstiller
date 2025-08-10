"""
ZIP 파일 처리기
압축 파일을 해제하고 내부 파일들을 추출합니다.
"""

import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
from .base import DocumentParser, ParseResult


class ZipParser(DocumentParser):
    """ZIP 압축 파일 처리기"""
    
    def __init__(self):
        super().__init__("zip_parser")
        
    def get_supported_extensions(self) -> List[str]:
        return ['.zip', '.ZIP']
    
    def parse(self, file_path: Path) -> ParseResult:
        """
        ZIP 파일을 해제하고 내부 파일 목록을 반환합니다.
        실제 파일 내용은 추출하지 않고 파일 목록만 생성합니다.
        """
        try:
            if not file_path.exists():
                return ParseResult(
                    success=False,
                    text="",
                    error_message=f"파일이 존재하지 않습니다: {file_path}",
                    parser_name=self.name
                )
            
            # ZIP 파일 검증
            if not zipfile.is_zipfile(file_path):
                return ParseResult(
                    success=False,
                    text="",
                    error_message="올바른 ZIP 파일이 아닙니다.",
                    parser_name=self.name
                )
            
            file_list = []
            total_size = 0
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    if not info.is_dir():  # 디렉토리는 제외
                        file_list.append({
                            'filename': info.filename,
                            'size': info.file_size,
                            'compressed_size': info.compress_size,
                            'modified': info.date_time
                        })
                        total_size += info.file_size
            
            # 파일 목록을 텍스트로 변환
            text_content = f"ZIP 파일 내용 ({len(file_list)}개 파일, 총 {total_size:,} bytes):\n\n"
            
            for file_info in file_list:
                text_content += f"📄 {file_info['filename']}\n"
                text_content += f"   크기: {file_info['size']:,} bytes\n"
                text_content += f"   압축 크기: {file_info['compressed_size']:,} bytes\n"
                text_content += f"   수정일: {'-'.join(map(str, file_info['modified'][:3]))}\n\n"
            
            return ParseResult(
                success=True,
                text=text_content,
                parser_name=self.name,
                metadata={
                    'file_count': len(file_list),
                    'total_size': total_size,
                    'files': file_list
                }
            )
            
        except zipfile.BadZipFile:
            return ParseResult(
                success=False,
                text="",
                error_message="손상된 ZIP 파일입니다.",
                parser_name=self.name
            )
        except Exception as e:
            return ParseResult(
                success=False,
                text="",
                error_message=f"ZIP 파일 처리 중 오류 발생: {str(e)}",
                parser_name=self.name
            )
    
    def extract_files(self, file_path: Path, extract_to: Path) -> Tuple[bool, List[Path], str]:
        """
        ZIP 파일을 지정된 디렉토리에 추출합니다.
        
        Returns:
            Tuple[bool, List[Path], str]: (성공여부, 추출된 파일 목록, 오류메시지)
        """
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
            extracted_files = []
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                for info in zip_ref.infolist():
                    if not info.is_dir():
                        # 안전한 경로 확인 (디렉토리 탐색 공격 방지)
                        if '..' in info.filename or info.filename.startswith('/'):
                            continue
                        
                        extract_path = extract_to / info.filename
                        extract_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        with zip_ref.open(info) as source, open(extract_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                        
                        extracted_files.append(extract_path)
            
            return True, extracted_files, ""
            
        except Exception as e:
            return False, [], f"ZIP 파일 추출 중 오류 발생: {str(e)}"